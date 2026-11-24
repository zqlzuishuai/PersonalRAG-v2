import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from auth_jwks.cloudflare import CfaAuthMiddleware, CloudFlareTokenValidation
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from starlette.types import ASGIApp

from auth import user_can_write_mcp
from auth_http import BearerAuthMiddleware, CloudflareUserBindingMiddleware, get_current_user_id
from config import Settings, required_env
from documents import (
    get_document,
    list_deleted_documents,
    list_document_versions,
    list_documents,
    move_document,
    rename_document,
    restore_document,
    set_document_tags,
    soft_delete_document,
    upload_bytes,
    upload_file,
)
from folder import (
    create_folder,
    list_deleted_folders,
    list_folders,
    move_folder,
    rename_folder,
    soft_delete_folder_tree,
)
from knowledge_service import fetch_knowledge, search_knowledge


async def require_mcp_write(settings: Settings) -> UUID:
    user_id = get_current_user_id()
    if not await asyncio.to_thread(user_can_write_mcp, settings, user_id):
        raise ToolError("当前账号未开启 MCP 写入权限")
    return user_id


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

    @mcp.tool()
    async def rag_create_folder(name: str, parent_id: UUID | None = None) -> dict[str, Any]:
        """创建文件夹

        Args:
            name (str): 文件夹名称
            parent_id (UUID | None, optional): 父文件夹ID. Defaults to None.

        Returns:
            dict: 创建的文件夹信息
        """
        user_id = await require_mcp_write(settings)
        folder_id= await asyncio.to_thread(
            create_folder,
            settings,
            user_id,
            name,
            parent_id
        )
        return {"folder_id": folder_id}

    @mcp.tool()
    async def rag_list_folders(parent_id: UUID | None = None) -> list[dict[str, Any]]:
        """列出文件夹

        Args:
            parent_id (UUID | None, optional): 父文件夹ID. Defaults to None.

        Returns:
            list: 文件夹列表
        """
        user_id = get_current_user_id()
        return await asyncio.to_thread(
            list_folders,
            settings,
            user_id,
            parent_id
        )


    @mcp.tool()
    async def rag_rename_folder(folder_id: UUID, new_name: str) -> None:
        """重命名文件夹

        Args:
            folder_id (UUID): 文件夹ID
            new_name (str): 新的文件夹名称
        """
        user_id = await require_mcp_write(settings)
        await asyncio.to_thread(
            rename_folder,
            settings,
            user_id,
            folder_id,
            new_name
        )

    @mcp.tool()
    async def rag_move_folder(folder_id: UUID, new_parent_id: UUID | None) -> None:
        """移动文件夹

        Args:
            folder_id (UUID): 文件夹ID
            new_parent_id (UUID | None): 新的父文件夹ID
        """
        user_id = await require_mcp_write(settings)
        await asyncio.to_thread(
            move_folder,
            settings,
            user_id,
            folder_id,
            new_parent_id
        )

    @mcp.tool()
    async def rag_soft_delete_folder(folder_id: UUID) -> dict[str, Any]:
        """软删除文件夹

        Args:
            folder_id (UUID): 文件夹ID
        Returns:
            dict[str, UUID]: 包含被删除的文件夹ID的字典
        """
        user_id = await require_mcp_write(settings)
        foler_id=await asyncio.to_thread(
            soft_delete_folder_tree,
            settings,
            user_id,
            folder_id,
        )
        return {"folder_id": foler_id}

    @mcp.tool()
    async def rag_list_deleted_folders(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """列出已删除的文件夹
        
        Args:
            limit (int, optional): 返回的文件夹数量限制. Defaults to 50.
            offset (int, optional): 返回的文件夹偏移量. Defaults to 0.

        Returns:
            list: 已删除的文件夹列表
        """
        user_id = get_current_user_id()
        return await asyncio.to_thread(
            list_deleted_folders,
            settings,
            user_id,
            limit,
            offset
        )







    # @mcp.tool()
    # async def rag_upload_file(
    #     file_path: Path,
    #     document_id: UUID | None = None,
    #     *
    #     ,folder_id: UUID | None = None
    # ) -> dict[str, Any]:
    #     """上传文件到指定文件夹

    #     Args:
    #         file_path (str): 文件路径
    #         folder_id (UUID | None, optional): 目标文件夹ID. Defaults to None.

    #     Returns:
    #         dict: 上传的文件信息
    #     """
    #     user_id = get_current_user_id()
    #     # 这里可以调用一个上传文件的函数，例如 upload_file_to_folder
    #     # 假设该函数返回上传的文件信息
    #     file_info = await asyncio.to_thread(
    #         upload_file,
    #         settings,
    #         user_id,
    #         file_path,
    #         document_id,
    #         folder_id=folder_id
    #     )
    #     return asdict(file_info)

    @mcp.tool()
    async def rag_upload_bytes(
        file_name: str,
        content: bytes,
        document_id: UUID | None = None,
        *,
        folder_id: UUID | None = None
    )-> dict[str, Any]:
        """上传字节内容到指定文件夹的指定文件

        Args:
            file_name (str): 文件名
            content (bytes): 文件内容
            folder_id (UUID | None, optional): 目标文件夹ID. Defaults to None.

        Returns:
            dict: 上传的文件信息
        """
        user_id = await require_mcp_write(settings)
        # 这里可以调用一个上传文件的函数，例如 upload_file_to_folder
        # 假设该函数返回上传的文件信息
        file_info = await asyncio.to_thread(
            upload_bytes,
            settings,
            user_id,
            file_name,
            content,
            document_id,
            folder_id=folder_id
        )
        return asdict(file_info)

    @mcp.tool()
    async def rag_list_documents(
        folder_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
        *,
        scope: str = "folder",
        q: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """列出指定文件夹下的文档

        Args:
            folder_id (UUID | None, optional): 目标文件夹ID. Defaults to None.
            limit (int, optional): 返回的文档数量限制. Defaults to 50.
            offset (int, optional): 返回的文档偏移量. Defaults to 0.
            scope (str, optional): 查询范围，支持 "folder" 或 "all". Defaults to "folder".
            q (str | None, optional): 查询关键字. Defaults to None.
            tags (list[str] | None, optional): 标签列表. Defaults to None.

        Returns:
            list: 文档列表
        """
        user_id = get_current_user_id()
        return await asyncio.to_thread(
            list_documents,
            settings,
            user_id,
            folder_id,
            limit,
            offset,
            scope=scope,
            q=q,
            tags=tags
        )

    @mcp.tool()
    async def rag_move_document(
        document_id: UUID,
        new_folder_id: UUID | None = None
    ) -> dict[str, Any]:
        """移动文档到指定文件夹

        Args:
            document_id (UUID): 文档ID
            new_folder_id (UUID | None, optional): 新的目标文件夹ID. Defaults to None.
        """
        user_id = await require_mcp_write(settings)
        document_id = await asyncio.to_thread(
            move_document,
            settings,
            user_id,
            document_id,
            new_folder_id
        )
        return {"document_id": document_id}

    @mcp.tool()
    async def rag_rename_document(
        document_id: UUID,
        new_title: str
    ) -> dict[str, Any]:
        """重命名文档

        Args:
            document_id (UUID): 文档ID
            new_name (str): 新的文档名称
        """
        user_id = await require_mcp_write(settings)
        document_id = await asyncio.to_thread(
            rename_document,
            settings,
            user_id,
            document_id,
            new_title
        )
        return {"document_id": document_id}

    @mcp.tool()
    async def rag_set_tags_document(
        document_id: UUID,
        tags: list[str]
    ) -> dict[str, Any]:
        """设置文档的标签

        Args:
            document_id (UUID): 文档ID
            tags (list[str]): 标签列表
        """
        user_id = await require_mcp_write(settings)
        document_id=await asyncio.to_thread(
            set_document_tags,
            settings,
            user_id,
            document_id,
            tags
        )
        return {"document_id": document_id}

    @mcp.tool()
    async def rag_soft_delete_document(
        document_id: UUID
    ) -> dict[str, Any]:
        """软删除文档

        Args:
            document_id (UUID): 文档ID
        """
        user_id = await require_mcp_write(settings)
        document_id=await asyncio.to_thread(
            soft_delete_document,
            settings,
            user_id,
            document_id,
        )
        return {"document_id": document_id}

    @mcp.tool()
    async def rag_list_deleted_documents(
        limit: int = 50,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """列出已删除的文档

        Args:
            limit (int, optional): 返回的文档数量限制. Defaults to 50.
            offset (int, optional): 返回的文档偏移量. Defaults to 0.

        Returns:
            list: 已删除的文档列表
        """
        user_id = get_current_user_id()
        return await asyncio.to_thread(
            list_deleted_documents,
            settings,
            user_id,
            limit,
            offset
        )

    @mcp.tool()
    async def rag_restore_document(
        document_id: UUID
    ) -> dict[str, Any]:
        """恢复已删除的文档

        Args:
            document_id (UUID): 文档ID
        """
        user_id = await require_mcp_write(settings)
        document_id=await asyncio.to_thread(
            restore_document,
            settings,
            user_id,
            document_id,
        )
        return {"document_id": document_id}

    @mcp.tool()
    async def rag_get_document(
        document_id: UUID
    ) -> dict[str, Any]:
        """获取文档信息

        Args:
            document_id (UUID): 文档ID
        """
        user_id = get_current_user_id()
        return await asyncio.to_thread(
            get_document,
            settings,
            user_id,
            document_id,
        )

    @mcp.tool()
    async def rag_list_versions_document(
        document_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """列出文档的版本信息

        Args:
            document_id (UUID): 文档ID
        """
        user_id = get_current_user_id()
        return await asyncio.to_thread(
            list_document_versions,
            settings,
            user_id,
            document_id,
            limit,
            offset
        )


    http_app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
    )
    cfa=CloudFlareTokenValidation(
        aud=required_env("PERSONALRAG_CFA_AUD"),
        team=required_env("PERSONALRAG_CFA_TEAM_DOMAIN"),
    )
    http_app.add_middleware(
        CloudflareUserBindingMiddleware,
        settings=settings,
        issuer=cfa.issuer
    )
    http_app.add_middleware(
        CfaAuthMiddleware,
        verify_token=cfa.verify_user
    )
    return http_app
    return CfaAuthMiddleware(http_app,verify_token=cfa.verify_user) 
    return BearerAuthMiddleware(http_app,settings)

def main():
    import uvicorn

    from config import load_settings
    settings =load_settings()
    app=create_app(settings)
    uvicorn.run(app,host=settings.mcp_host,port=settings.mcp_port)

if __name__ == "__main__":
    main()
