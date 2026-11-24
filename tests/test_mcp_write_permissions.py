import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.testclient import TestClient

from auth_http import current_user_id
from mcp_server import create_app


class MCPWritePermissionsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = UUID("11111111-1111-4111-8111-111111111111")
        self.item_id = "22222222-2222-4222-8222-222222222222"
        self.settings = SimpleNamespace(mcp_port=8000)
        token = current_user_id.set(self.user_id)
        self.addCleanup(current_user_id.reset, token)
        with (
            patch.object(
                MCPServer, "streamable_http_app", autospec=True,
                side_effect=MCPServer.streamable_http_app,
            ) as streamable_http_app,
            patch("mcp_server.CloudFlareTokenValidation"),
            patch("mcp_server.required_env", return_value="test-config"),
        ):
            create_app(self.settings)
            self.mcp = streamable_http_app.call_args.args[0]

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

    async def test_read_only_tool_discovery_hides_all_write_tools(self):
        by_name = {tool.name: tool for tool in await self.mcp.list_tools()}
        self.assertEqual(set(by_name), {
            "rag_search", "rag_fetch", "rag_list_folders", "rag_list_deleted_folders",
            "rag_list_documents", "rag_list_deleted_documents", "rag_get_document",
            "rag_list_versions_document",
        })
        self.assertIn("当前账号为只读", by_name["rag_search"].description)

    async def test_tool_discovery_for_write_enabled_user(self):
        self.connection.execute.return_value.fetchone.return_value = (True,)
        by_name = {tool.name: tool for tool in await self.mcp.list_tools()}
        self.assertIn("rag_rename_document", by_name)
        self.assertIn("rag_upload_bytes", by_name)
        self.assertNotIn("当前账号为只读", by_name["rag_search"].description)


class MCPHostTests(unittest.TestCase):
    def test_only_public_and_configured_loopback_hosts_are_accepted(self):
        async def verify_user(_token):
            return SimpleNamespace(sub="test-user")

        request = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "test", "version": "1"}},
        }
        cases = {"mcp.191226269.xyz": 200, "127.0.0.1:8000": 200,
                 "127.0.0.1:8002": 421, "other.example.test": 421}
        with (
            patch("mcp_server.CloudFlareTokenValidation") as validator,
            patch("mcp_server.required_env", return_value="test-config"),
            patch("auth_http.resolve_cloudflare_user_id", return_value=UUID(int=1)),
            patch("mcp_server.user_can_write_mcp", return_value=False),
        ):
            validator.return_value.verify_user = verify_user
            app = create_app(SimpleNamespace(mcp_port=8000))
            with TestClient(app) as client:
                for host, expected in cases.items():
                    with self.subTest(host=host):
                        response = client.post("/mcp", headers={
                            "Host": host,
                            "Cf-Access-Jwt-Assertion": "test-token",
                            "Accept": "application/json, text/event-stream",
                        }, json=request)
                        self.assertEqual(response.status_code, expected, response.text)

                public_headers = {"Host": "mcp.191226269.xyz",
                                  "Accept": "application/json, text/event-stream"}
                self.assertEqual(client.post("/mcp", headers=public_headers, json=request).status_code, 401)
                public_headers["Cf-Access-Jwt-Assertion"] = "test-token"
                listing = client.post("/mcp", headers=public_headers, json={
                    "jsonrpc": "2.0", "id": 2, "method": "tools/list",
                })
                self.assertEqual(listing.status_code, 200, listing.text)
                tools = {tool["name"] for tool in listing.json()["result"]["tools"]}
                self.assertIn("rag_search", tools)
                self.assertNotIn("rag_upload_bytes", tools)
