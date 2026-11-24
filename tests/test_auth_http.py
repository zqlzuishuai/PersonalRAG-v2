import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from auth_http import (
    CloudflareUserBindingMiddleware,
    get_current_user_id,
)


class CloudflareUserBindingMiddlewareTests(unittest.TestCase):
    def test_sets_local_user_for_request_and_resets_context(self):
        local_user_id = UUID("11111111-1111-4111-8111-111111111111")
        settings = object()
        issuer = "https://team.cloudflareaccess.com"

        async def set_verified_identity(request, call_next):
            if request.headers.get("Cf-Access-Jwt-Assertion") == "valid-token":
                request.state.user = SimpleNamespace(sub="cloudflare-user-sub")
            return await call_next(request)

        async def endpoint(request):
            return JSONResponse({"user_id": str(get_current_user_id())})

        app = Starlette(routes=[Route("/", endpoint)])
        app.add_middleware(
            CloudflareUserBindingMiddleware,
            settings=settings,
            issuer=issuer,
        )
        app.add_middleware(BaseHTTPMiddleware, dispatch=set_verified_identity)

        with patch(
            "auth_http.resolve_cloudflare_user_id",
            return_value=local_user_id,
        ) as authenticate:
            with TestClient(app) as client:
                response = client.get(
                    "/",
                    headers={"Cf-Access-Jwt-Assertion": "valid-token"},
                )
                self.assertEqual(client.get("/").status_code, 403)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_id": "11111111-1111-4111-8111-111111111111"},
        )
        authenticate.assert_called_once_with(
            settings,
            issuer,
            "cloudflare-user-sub",
        )
        with self.assertRaises(PermissionError):
            get_current_user_id()


if __name__ == "__main__":
    unittest.main()
