"""How responses reach the browser: compression, caching, bundling.

Split out of app.py, which had grown past its size budget, and
because these three are one concern: what the client receives on the
wire rather than what the app computes.

Compression happens here rather than at the proxy because Caddy 2 has
no built-in brotli, and every response this app serves — HTML, CSS,
JS, JSON, the sitemap — is text. The document alone was 92 KB. Nothing
user-supplied is reflected into a compressed response alongside a
secret, so the BREACH class of attack does not apply.
"""
from __future__ import annotations

import os

from flask import request
from flask_compress import Compress

# Text this app actually serves. Images and PDFs are already
# compressed and only get bigger for the CPU spent.
MIMETYPES = [
    "text/html", "text/css", "text/xml", "text/plain",
    "application/javascript", "text/javascript",
    "application/json", "application/xml", "image/svg+xml",
]

# How long a response may be reused. Static assets are fingerprinted
# by ?v= (see app.inject_js_version), so the bytes behind one of those
# URLs never change and a year is safe. Anything unversioned — the
# vendored Chart.js, the favicons — must stay bustable, or a fix would
# be stranded behind a URL nobody can change. HTML revalidates every
# time: it is generated per language and per request.
IMMUTABLE = "public, max-age=31536000, immutable"
UNVERSIONED = "public, max-age=3600"
REVALIDATE = "public, max-age=0, must-revalidate"

# The simulator page's module scripts, in load order. One list, used
# by the template's no-bundle fallback and mirrored by
# static/js/entry.index.js; tests/test_delivery.py fails if the two
# disagree.
INDEX_MODULES = [
    "data", "calc", "chart", "scenarios", "ui", "pension1",
    "pension3", "property", "export", "accordion", "info",
]


def _cache_policy(resp):
    """Set Cache-Control, unless the route already chose one: the PDF
    export and the JSON APIs opt out of caching entirely."""
    if request.path.startswith("/static/"):
        # Assigned, not defaulted: Flask's own static handler already
        # sets "no-cache", so setdefault would never fire.
        resp.headers["Cache-Control"] = (
            IMMUTABLE if request.args.get("v") else UNVERSIONED)
        return resp
    if resp.content_type.startswith("text/html"):
        resp.headers.setdefault("Cache-Control", REVALIDATE)
    return resp


def _bundle_globals(static_folder):
    """Serve the built bundle when tools/build-js.sh has produced one,
    else the individual modules.

    Production ships the bundle; it is committed, like
    static/css/tailwind.css, because the image carries no Node. The
    fallback is what makes local editing work: a developer who changes
    a module and reloads sees the change without rebuilding first."""
    built = os.path.join(static_folder, "js", "bundle")
    return {
        "index_modules": INDEX_MODULES,
        "has_index_bundle": os.path.exists(
            os.path.join(built, "index.js")),
        "has_loans_bundle": os.path.exists(
            os.path.join(built, "loans.js")),
    }


def init_app(app):
    """Turn on compression, caching and the bundle switch."""
    app.config.update(
        COMPRESS_ALGORITHM=["br", "gzip"],
        COMPRESS_MIMETYPES=MIMETYPES,
        COMPRESS_MIN_SIZE=500,
        # Brotli 5 costs a few milliseconds more than the default and
        # gives most of what the slow levels do; gzip 6 is zlib's own
        # default balance.
        COMPRESS_BR_LEVEL=5,
        COMPRESS_LEVEL=6,
    )
    Compress(app)
    app.after_request(_cache_policy)
    app.context_processor(
        lambda: _bundle_globals(app.static_folder))
