import asyncio
import unittest
from uuid import uuid4

from langchain_core.messages import ToolMessage

from agent_service import stream_agent


class RecordingAgent:
    def __init__(self):
        self.inputs = []

    async def astream(self, input_data, *, config, stream_mode):
        self.inputs.append(input_data)
        if False:
            yield None


class ToolResultAgent:
    async def astream(self, input_data, *, config, stream_mode):
        yield (
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content="检索结果正文",
                            name="rag_search",
                            tool_call_id="call-1",
                        )
                    ]
                }
            },
        )


class StreamAgentTests(unittest.TestCase):
    def test_stream_agent_sends_user_query_in_messages(self):
        agent = RecordingAgent()

        async def run():
            return [
                event
                async for event in stream_agent(
                    agent,
                    uuid4(),
                    "代码里的提问",
                )
            ]

        asyncio.run(run())

        self.assertEqual(
            agent.inputs,
            [{"messages": [{"role": "user", "content": "代码里的提问"}]}],
        )

    def test_stream_agent_includes_tool_result_text(self):
        async def run():
            return [
                event
                async for event in stream_agent(
                    ToolResultAgent(),
                    uuid4(),
                    "检索问题",
                )
            ]

        self.assertEqual(
            asyncio.run(run()),
            [
                {
                    "type": "tool_result",
                    "name": "rag_search",
                    "id": "call-1",
                    "status": "success",
                    "text": "检索结果正文",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
