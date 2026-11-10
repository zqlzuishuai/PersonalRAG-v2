"""Plain-HTTP visitors must be moved to HTTPS before any credential is typed."""
import unittest

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from web_app import ForceHTTPSMiddleware


async def page(request):
    return JSONResponse({"ok": True})


async def api(request):
    return JSONResponse({"ok": True})


def make_client(base_url, client_addr=None):
    app = Starlette(
        routes=[
            Route("/register", page, methods=["GET"]),
            Route("/api/auth/register", api, methods=["POST"]),
        ],
        middleware=[Middleware(ForceHTTPSMiddleware)],
    )
    if client_addr:
        return TestClient(
            app, base_url=base_url, client=client_addr, follow_redirects=False
        )
    return TestClient(app, base_url=base_url, follow_redirects=False)


class ForceHTTPSMiddlewareTests(unittest.TestCase):
    def test_https_request_passes_through(self):
        client = make_client("https://rag.example.test")
        self.assertEqual(client.get("/register").status_code, 200)

    def test_forwarded_http_page_redirects(self):
        client = make_client("http://rag.example.test")
        response = client.get("/register", headers={"x-forwarded-proto": "http"})
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.headers["location"], "https://rag.example.test/register")

    def test_forwarded_http_query_string_kept(self):
        client = make_client("http://rag.example.test")
        response = client.get("/register?from=wechat", headers={"x-forwarded-proto": "http"})
        self.assertEqual(
            response.headers["location"], "https://rag.example.test/register?from=wechat"
        )

    def test_forwarded_http_write_request_rejected(self):
        client = make_client("http://rag.example.test")
        response = client.post(
            "/api/auth/register",
            headers={"x-forwarded-proto": "http"},
            json={"login_name": "alice", "password": "a-long-password"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("HTTPS", response.json()["error"])

    def test_loopback_without_proxy_header_allowed(self):
        client = make_client("http://127.0.0.1:8001", client_addr=("127.0.0.1", 50000))
        self.assertEqual(client.get("/register").status_code, 200)

    def test_plain_http_from_remote_client_redirects(self):
        client = make_client("http://rag.example.test", client_addr=("203.0.113.9", 50000))
        self.assertEqual(client.get("/register").status_code, 308)

    def test_forwarded_https_not_redirected(self):
        client = make_client("http://rag.example.test")
        response = client.get("/register", headers={"x-forwarded-proto": "https"})
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
