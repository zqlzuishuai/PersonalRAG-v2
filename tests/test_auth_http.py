import unittest
from unittest.mock import patch
from uuid import UUID

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from auth_http import (
    CloudflareAccessAuthMiddleware,
    get_current_user_id,
)


class CloudflareAccessAuthMiddlewareTests(unittest.TestCase):
    def test_sets_local_user_for_request_and_resets_context(self):
        local_user_id = UUID("11111111-1111-4111-8111-111111111111")
        settings = object()

        async def verify_token(token):
            if token != "valid-token":
                raise ValueError("invalid token")
            return {
                "iss": "https://team.cloudflareaccess.com",
                "sub": "cloudflare-user-sub",
            }

        async def endpoint(request):
            return JSONResponse({"user_id": str(get_current_user_id())})

        app = Starlette(routes=[Route("/", endpoint)])
        app.add_middleware(
            CloudflareAccessAuthMiddleware,
            settings=settings,
            verify_token=verify_token,
        )

        with patch(
            "auth_http.authenticate_cloudflare_identity",
            return_value=local_user_id,
        ) as authenticate:
            with TestClient(app) as client:
                response = client.get(
                    "/",
                    headers={"Cf-Access-Jwt-Assertion": "valid-token"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_id": "11111111-1111-4111-8111-111111111111"},
        )
        authenticate.assert_called_once_with(
            settings,
            "https://team.cloudflareaccess.com",
            "cloudflare-user-sub",
        )
        with self.assertRaises(PermissionError):
            get_current_user_id()


if __name__ == "__main__":
    unittest.main()
