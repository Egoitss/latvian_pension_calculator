"""Root-level discovery files: robots.txt and sitemap.xml.

Both were missing — a crawler asking for either got the app's 404 —
so nothing pointed search engines at the two language trees.

The sitemap carries the same hreflang triplet the page head does (see
base.html). A sitemap that disagrees with the markup is worse than
one that stays silent: the two are competing claims about the same
pair, and a crawler discards both. Kept in one module so the pairing
rule has a single home.
"""
from __future__ import annotations

from flask import Blueprint, Response

from data import DATA_UPDATED

SITE = "https://pension.oats.lv"
# Discovery files change only on deploy, and a crawler that
# re-reads them hourly is doing no harm either way.
CACHE = "public, max-age=3600"
XHTML_NS = "http://www.w3.org/1999/xhtml"

# The Latvian half of every indexable page. English twins are derived,
# never listed by hand, so the two halves cannot drift apart.
#
# /loans is here as well as the simulator: it is a separate tool on
# the same site, indexable and linked, and a sitemap that omitted it
# would be incomplete on the day it shipped.
LV_PATHS = ["/", "/loans"]

bp = Blueprint("seo", __name__)


def en_path(path: str) -> str:
    """The English twin of a Latvian path. The English root is /en,
    with no trailing slash; every other page keeps its own path under
    the prefix. Mirrors app._alt_path in the other direction."""
    return "/en" + ("" if path == "/" else path)


def _alternates(lv: str) -> str:
    """The xhtml:link set Google expects inside a <url>: both language
    versions, this one included, plus x-default on Latvian."""
    return "".join(
        f'<xhtml:link rel="alternate" hreflang="{code}"'
        f' href="{SITE}{path}"/>'
        for code, path in (("lv", lv), ("en", en_path(lv)),
                           ("x-default", lv)))


def sitemap_xml(lastmod: str) -> str:
    """The whole sitemap. Each <url> stays on one line, annotations
    included, so the file reads as one row per URL."""
    rows = "\n".join(
        f"  <url><loc>{SITE}{url}</loc>"
        f"<lastmod>{lastmod}</lastmod>{_alternates(lv)}</url>"
        for lv in LV_PATHS for url in (lv, en_path(lv)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            f'        xmlns:xhtml="{XHTML_NS}">\n'
            f"{rows}\n</urlset>\n")


@bp.get("/robots.txt")
def robots():
    """Allow all crawlers; point them at the sitemap."""
    body = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"
    return Response(body, mimetype="text/plain",
                    headers={"Cache-Control": CACHE})


@bp.get("/sitemap.xml")
def sitemap():
    """Both language trees, with their hreflang pairing.

    lastmod is DATA_UPDATED, the date the rates and plan data were
    last checked, which is also what the footer shows. Today's date
    would claim the pages change daily; they do not, and a lastmod a
    crawler can see is untrue is worse than none."""
    return Response(sitemap_xml(DATA_UPDATED),
                    mimetype="application/xml",
                    headers={"Cache-Control": CACHE})
