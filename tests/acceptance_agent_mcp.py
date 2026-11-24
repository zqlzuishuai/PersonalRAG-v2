"""Run with `python -B -m tests.acceptance_agent_mcp` from the project root."""

import asyncio
import json
import logging
import socket
from uuid import uuid4
from unittest.mock import patch

import httpx
import uvicorn
from langchain_core.messages import AIMessage

from agent_service import agent_session, stream_agent
from config import load_settings
from mcp_server import create_app
from tests.test_agent_limits import FakeToolCallingModel


async def run_acceptance():
    settings = load_settings()
    user_id = uuid4()
    chunk_id = str(uuid4())
    token = "acceptance-local-fixture"
    fact = "The archive number is QC-7319."
    question = "Search for the archive number, then fetch its source."
    calls = []

    def authenticate(_, presented_token):
        if presented_token != token:
            raise PermissionError()
        return user_id

    def search(_, caller_id, query, *, top_k):
        assert caller_id == user_id
        calls.append("rag_search")
        return [{"chunk_id": chunk_id, "content": fact}]

    def fetch(_, caller_id, requested_chunk_id):
        assert caller_id == user_id and str(requested_chunk_id) == chunk_id
        calls.append("rag_fetch")
        return {"chunk_id": chunk_id, "content": fact}

    def model(_):
        replies = [
            AIMessage(content="", tool_calls=[{
                "name": "rag_search", "args": {"query": "archive number"}, "id": "search-1",
            }]),
            AIMessage(content="", tool_calls=[{
                "name": "rag_fetch", "args": {"chunk_id": chunk_id}, "id": "fetch-1",
            }]),
            AIMessage(content=f"{fact} Source: {chunk_id}"),
        ]
        return FakeToolCallingModel(messages=iter(replies), disable_streaming=True)

    with (
        patch("auth_http.authenticate_token", side_effect=authenticate),
        patch("mcp_server.search_knowledge", side_effect=search),
        patch("mcp_server.fetch_knowledge", side_effect=fetch),
        patch("agent_service.create_chat_model", side_effect=model),
        socket.socket() as sock,
    ):
        sock.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{sock.getsockname()[1]}/mcp"
        server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="error"))
        server_task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            while not server.started:
                if server_task.done():
                    await server_task
                    raise RuntimeError("Local MCP server stopped during startup")
                await asyncio.sleep(0.02)

            async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
                missing = await client.post(url)
                invalid = await client.post(url, headers={"Authorization": "Bearer invalid"})
            assert missing.status_code == invalid.status_code == 401
            print("MCP HTTP rejects missing and invalid credentials with 401", flush=True)

            null_updates = []
            async with agent_session(settings, url, token) as agent:
                async for update in agent.astream(
                    {"messages": [{"role": "user", "content": question}]},
                    config={"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 12},
                    stream_mode="updates",
                ):
                    null_updates.extend(node for node, payload in update.items() if payload is None)
            assert calls == ["rag_search", "rag_fetch"], calls
            print(json.dumps({"raw_graph_tools": calls, "nodes_with_null_updates": null_updates}), flush=True)

            calls.clear()
            events = []
            async with agent_session(settings, url, token) as agent:
                async for event in stream_agent(agent, uuid4(), question):
                    events.append(event)
                    print(json.dumps({
                        "type": event["type"],
                        "name": event.get("name"),
                        "id": event.get("id"),
                        "status": event.get("status"),
                    }), flush=True)

            assert calls == ["rag_search", "rag_fetch"], calls
            by_id = {(event["type"], event.get("id")): event for event in events}
            for name, call_id in [("rag_search", "search-1"), ("rag_fetch", "fetch-1")]:
                request = by_id[("tool_requested", call_id)]
                response = by_id[("tool_result", call_id)]
                assert request["name"] == response["name"] == name
                assert response["status"] == "success"
            answer = "".join(event["text"] for event in events if event["type"] == "text")
            assert fact in answer and chunk_id in answer
            print("Agent stream reports both tools and the final sourced answer", flush=True)
        finally:
            server.should_exit = True
            await server_task


if __name__ == "__main__":
    logging.disable(logging.INFO)
    asyncio.run(asyncio.wait_for(run_acceptance(), timeout=30))
