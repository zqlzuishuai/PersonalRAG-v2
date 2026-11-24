"""Static frontend must work even with Windows registry MIME overrides."""
import mimetypes
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from starlette.applications import Starlette
from starlette.testclient import TestClient

from web_app import create_app
from web_frontend import add_frontend_routes


class FrontendStaticTests(unittest.TestCase):
    def test_vue_homepage_and_password_session_do_not_require_cloudflare_identity(self):
        origin = "https://rag.example.test"
        user_id = UUID(int=1)
        env = {
            "PERSONALRAG_WEB_SESSION_SECRET": "test-session-key",
            "PERSONALRAG_WEB_ORIGIN": origin,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / "frontend" / "dist"
            (dist / "assets").mkdir(parents=True)
            (dist / "index.html").write_text('<div id="app"></div>', encoding="utf-8")
            with (
                patch("web_app.Path", return_value=root / "web_app.py"),
                patch("web_app.required_env", side_effect=env.__getitem__),
                patch("web_app.env_bool", side_effect=lambda key, default: key != "PERSONALRAG_WEB_DEBUG"),
                patch("web_app.load_settings", return_value=object()),
                patch("web_app.authenticate_password", return_value=user_id),
                TestClient(create_app(), base_url=origin) as client,
            ):
                homepage = client.get("/")
                self.assertEqual(homepage.status_code, 200, homepage.text)
                self.assertIn('<div id="app"></div>', homepage.text)
                self.assertEqual(client.get("/api/auth/me").status_code, 401)
                response = client.post("/api/auth/login", headers={"Origin": origin},
                                       json={"login_name": "alice", "password": "test-password"})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(client.get("/api/auth/me").json(), {"user_id": str(user_id)})

    def test_javascript_mime_and_nested_assets(self):
        previous = mimetypes.guess_type('app.js')[0]
        try:
            mimetypes.add_type('text/plain', '.js')
            with tempfile.TemporaryDirectory() as directory:
                dist = Path(directory)
                (dist / 'assets' / 'rhine').mkdir(parents=True)
                (dist / 'index.html').write_text('<div id="app"></div>', encoding='utf-8')
                (dist / 'assets' / 'app.js').write_text('export const ready = true', encoding='utf-8')
                (dist / 'assets' / 'rhine' / 'sample.txt').write_text('fixture', encoding='utf-8')
                app = Starlette()
                add_frontend_routes(app, dist)
                with TestClient(app) as client:
                    script = client.get('/assets/app.js')
                    self.assertEqual(script.status_code, 200)
                    self.assertIn(script.headers['content-type'].split(';')[0], ('text/javascript', 'application/javascript'))
                    self.assertEqual(client.get('/assets/rhine/sample.txt').text, 'fixture')
                    self.assertEqual(client.get('/login').status_code, 200)
                    self.assertEqual(client.get('/api/unknown').status_code, 404)
        finally:
            if previous:
                mimetypes.add_type(previous, '.js')


if __name__ == '__main__':
    unittest.main()
