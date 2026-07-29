"""Cross-subdomain language preference for pension.oats.lv.

Routing itself is already path-based: Latvian at the bare path,
English under ``/en``. This module only adds the shared ``oats_lang``
cookie so a language chosen on any OATS property carries to the
others, and the one place it is read.

The cookie never changes what a given URL serves. It is consulted for
a visitor arriving at the site root from somewhere else, and nowhere
else, so every URL stays self-canonical for crawlers and stable as a
shared link. Mirrors bmx.oats.lv's ``web/langpath.py``.
"""
from __future__ import annotations

from flask import Response, redirect, request

COOKIE = "oats_lang"
COOKIE_DOMAIN = ".oats.lv"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60          # one year
PREFIX = "/en"


def entry_redirect() -> Response | None:
    """Send a visitor whose stored language is English from the site
    root to the English root.

    Only the root, and only when the navigation did not come from this
    same origin. Without that second condition the English cookie would
    bounce the LV switcher (which points at ``/``) straight back to
    ``/en``, and the visitor could never return to Latvian. A missing
    Sec-Fetch-Site header means an old browser or a crawler, so the
    safe answer there is to serve the page as asked.
    """
    if request.path != "/" or request.cookies.get(COOKIE) != "en":
        return None
    if request.headers.get("Sec-Fetch-Site", "same-origin") == "same-origin":
        return None
    return redirect(PREFIX, code=302)


def remember(resp: Response, lang: str) -> Response:
    """Record the language of the page just served. Readable by script
    because the static oats.lv site has no server to set it."""
    resp.set_cookie(
        COOKIE, lang,
        max_age=COOKIE_MAX_AGE, domain=COOKIE_DOMAIN, path="/",
        secure=request.is_secure, httponly=False, samesite="Lax")
    return resp
