import asyncio
from typing import Annotated, Any
from uuid import UUID

from mcp.server import MCPServer
from pydantic import Field
from starlette.types import ASGIApp

from auth_http import BearerAuthMiddleware, get_current_user_id
from config import Settings
from knowledge_service import fetch_knowledge, search_knowledge


def create_app(settings: Settings) -> ASGIApp:
    mcp= MCPServer("PersonalRAG")

    @mcp.tool()
    async def rag_search(query: str,top_k: Annotated[int,Field(strict=True,ge=1,le=20)] = 5) -> list[dict[str, Any]]:
        """RAG检索工具

        Args:
            query (str): 检索的查询
            top_k (int, optional): 返回的top k结果. Defaults to 5.

        Returns:
            list: 检索结果列表
        """
        user_id = get_current_user_id()

        return await asyncio.to_thread(
            search_knowledge,
            settings,
            user_id,
            query,
            top_k=top_k
        )

    @mcp.tool()
    async def rag_fetch(chunk_id: UUID)-> dict[str,Any]:
        """RAG检索工具

        Args:
            chunk_id (UUID): 检索的片段id
        Returns:
            list: 检索结果
        """
        user_id = get_current_user_id()

        return await asyncio.to_thread(
            fetch_knowledge,
            settings,
            user_id,
            chunk_id
        )

    http_app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
    )

    return BearerAuthMiddleware(http_app,settings)

def main():
    import uvicorn

    from config import load_settings
    settings =load_settings()
    app=create_app(settings)
    uvicorn.run(app,host=settings.mcp_host,port=settings.mcp_port)

if __name__ == "__main__":
    main()