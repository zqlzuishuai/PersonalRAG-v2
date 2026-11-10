"""Origin guard must keep CSRF protection while tolerating in-app WebViews."""
import unittest

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from origin_guard import origin_allowed

ORIGIN = "https://rag.example.test"


async def probe(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)
    return JSONResponse({"ok": True})


def make_client():
    app = Starlette(routes=[Route("/api/probe", probe, methods=["POST"])])
    app.state.web_origin = ORIGIN
    return TestClient(app)


class OriginGuardTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()

    def post(self, **headers):
        return self.client.post("/api/probe", headers=headers, json={}).status_code

    def test_exact_origin_allowed(self):
        self.assertEqual(self.post(origin=ORIGIN), 200)

    def test_foreign_origin_rejected(self):
        self.assertEqual(self.post(origin="https://evil.test"), 403)

    def test_foreign_origin_with_our_referer_rejected(self):
        self.assertEqual(
            self.post(origin="https://evil.test", referer=f"{ORIGIN}/register"), 403
        )

    def test_missing_origin_without_signals_rejected(self):
        self.assertEqual(self.post(), 403)

    def test_null_origin_with_same_origin_fetch_metadata_allowed(self):
        client = self.client
        response = client.post(
            "/api/probe",
            headers={"origin": "null", "sec-fetch-site": "same-origin"},
            json={},
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_origin_with_our_referer_allowed(self):
        self.assertEqual(self.post(referer=f"{ORIGIN}/register"), 200)

    def test_null_origin_with_our_referer_allowed(self):
        self.assertEqual(
            self.post(origin="null", referer=f"{ORIGIN}/register?from=wechat"), 200
        )

    def test_null_origin_with_foreign_referer_rejected(self):
        self.assertEqual(
            self.post(origin="null", referer="https://evil.test/register"), 403
        )

    def test_missing_origin_with_cross_site_fetch_metadata_rejected(self):
        client = self.client
        response = client.post(
            "/api/probe",
            headers={"sec-fetch-site": "cross-site", "referer": "https://evil.test/"},
            json={},
        )
        self.assertEqual(response.status_code, 403)

    def test_referer_on_other_port_rejected(self):
        self.assertEqual(self.post(referer="https://rag.example.test:8443/register"), 403)


if __name__ == "__main__":
    unittest.main()
