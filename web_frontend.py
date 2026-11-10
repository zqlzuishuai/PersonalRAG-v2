"""Serve the built Vue application through the same origin as the API."""
import mimetypes
from pathlib import Path

from starlette.responses import FileResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles


def add_frontend_routes(app, dist: Path) -> None:
    dist = dist.resolve()
    if not (dist / "index.html").is_file() or not (dist / "assets").is_dir():
        raise RuntimeError("Missing Vue build: deploy frontend/dist before enabling the frontend")

    # Windows registry associations can report .js as text/plain. Module scripts
    # require a JavaScript MIME type, regardless of the host's file association.
    mimetypes.add_type("text/javascript", ".js")

    async def page(request):
        return FileResponse(
            dist / "index.html",
            headers={"Cache-Control": "no-cache"},
        )

    async def favicon(request):
        return FileResponse(dist / "favicon.ico")

    app.router.routes.append(Mount("/assets", StaticFiles(directory=dist / "assets")))
    for path in ("/", "/login", "/register", "/library", "/search", "/trash", "/documents/{document_id:uuid}"):
        app.router.routes.append(Route(path, page, methods=["GET"]))
    if (dist / "favicon.ico").is_file():
        app.router.routes.append(Route("/favicon.ico", favicon, methods=["GET"]))
