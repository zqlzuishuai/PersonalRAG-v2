"""Origin check for state-changing API requests.

Chrome, Firefox and Safari send `Origin` on every same-origin POST. Some
in-app WebViews (WeChat's X5 kernel, older WKWebView) send the literal
string "null" instead, or drop the header entirely. Treating those as
foreign makes every write endpoint fail inside WeChat, so such requests are
accepted only when the browser marks them same-origin (`Sec-Fetch-Site`) or
the `Referer` proves they came from our own page. A cross-site page cannot
forge either signal, so CSRF protection is unchanged.
"""
import logging
from urllib.parse import urlsplit

logger = logging.getLogger("uvicorn.error")


def _referer_is_ours(referer, expected):
    if not referer:
        return False
    try:
        parts = urlsplit(referer)
    except ValueError:
        return False
    if not parts.scheme or not parts.netloc:
        return False
    return f"{parts.scheme}://{parts.netloc}" == expected


def origin_allowed(request):
    expected = request.app.state.web_origin
    origin = request.headers.get("origin")
    if origin == expected:
        return True
    if origin is None or origin == "null":
        fetch_site = request.headers.get("sec-fetch-site")
        referer = request.headers.get("referer")
        if fetch_site == "same-origin" or _referer_is_ours(referer, expected):
            logger.info(
                "origin fallback accepted path=%s origin=%r sec-fetch-site=%r"
                " referer=%r",
                request.url.path,
                origin,
                fetch_site,
                (referer or "")[:120],
            )
            return True
    logger.warning(
        "origin rejected path=%s origin=%r sec-fetch-site=%r referer=%r ua=%r",
        request.url.path,
        origin,
        request.headers.get("sec-fetch-site"),
        (request.headers.get("referer") or "")[:120],
        (request.headers.get("user-agent") or "")[:100],
    )
    return False
