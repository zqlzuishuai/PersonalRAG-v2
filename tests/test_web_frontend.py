"""Static frontend must work even with Windows registry MIME overrides."""
import mimetypes
import tempfile
import unittest
from pathlib import Path

from starlette.applications import Starlette
from starlette.testclient import TestClient

from web_frontend import add_frontend_routes


class FrontendStaticTests(unittest.TestCase):
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
