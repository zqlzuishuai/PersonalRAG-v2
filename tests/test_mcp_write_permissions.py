import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from auth_http import current_user_id
from mcp_server import create_app


class MCPWritePermissionsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = UUID("11111111-1111-4111-8111-111111111111")
        self.item_id = "22222222-2222-4222-8222-222222222222"
        self.settings = SimpleNamespace()
        self.mcp = MCPServer("Permission tests")
        token = current_user_id.set(self.user_id)
        self.addCleanup(current_user_id.reset, token)
        with (
            patch("mcp_server.MCPServer", return_value=self.mcp),
            patch("mcp_server.CloudFlareTokenValidation"),
            patch("mcp_server.required_env", return_value="test-config"),
        ):
            create_app(self.settings)

        self.connection = MagicMock()
        self.connection.execute.return_value.fetchone.return_value = (False,)
        factory = self.enterContext(patch("auth.auth_connection"))
        factory.return_value.__enter__.return_value = self.connection

    async def test_read_only_user_cannot_call_any_write_tool(self):
        folder = {"folder_id": self.item_id}
        document = {"document_id": self.item_id}
        cases = {
            "rag_create_folder": ("create_folder", {"name": "test"}),
            "rag_rename_folder": ("rename_folder", {**folder, "new_name": "test"}),
            "rag_move_folder": ("move_folder", {**folder, "new_parent_id": None}),
            "rag_soft_delete_folder": ("soft_delete_folder_tree", folder),
            "rag_upload_bytes": ("upload_bytes", {"file_name": "test.txt", "content": b"test"}),
            "rag_move_document": ("move_document", document),
            "rag_rename_document": ("rename_document", {**document, "new_title": "test"}),
            "rag_set_tags_document": ("set_document_tags", {**document, "tags": ["test"]}),
            "rag_soft_delete_document": ("soft_delete_document", document),
            "rag_restore_document": ("restore_document", document),
        }
        for name, (operation, arguments) in cases.items():
            with self.subTest(tool=name), patch(f"mcp_server.{operation}") as write:
                with self.assertRaisesRegex(ToolError, "未开启 MCP 写入权限"):
                    await self.mcp.call_tool(name, arguments)
                write.assert_not_called()

    async def test_enabled_user_writes_using_authenticated_user_id(self):
        self.connection.execute.return_value.fetchone.return_value = (True,)
        with patch("mcp_server.rename_document", return_value=UUID(self.item_id)) as write:
            await self.mcp.call_tool(
                "rag_rename_document", {"document_id": self.item_id, "new_title": "test"}
            )
        write.assert_called_once_with(self.settings, self.user_id, UUID(self.item_id), "test")
        self.connection.execute.assert_called_once()
        self.assertEqual(self.connection.execute.call_args.args[1], (self.user_id,))

    async def test_read_tool_does_not_require_write_permission(self):
        with patch("mcp_server.search_knowledge", return_value=[]) as search:
            await self.mcp.call_tool("rag_search", {"query": "test"})
        search.assert_called_once_with(self.settings, self.user_id, "test", top_k=5)
        self.connection.execute.assert_not_called()
