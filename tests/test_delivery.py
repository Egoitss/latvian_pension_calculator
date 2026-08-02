"""How responses reach the browser: encoding, caching, discovery.

The app served 92 KB of uncompressed HTML with no-store on everything
and answered 404 for robots.txt and sitemap.xml. These pin the four
fixes, and the boundaries where each stops applying.
"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import delivery                    # noqa: E402
import seo                         # noqa: E402
from app import app                # noqa: E402

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
XHTML = "{http://www.w3.org/1999/xhtml}link"


def get(path, encoding="br, gzip"):
    return app.test_client().get(
        path, headers={"Accept-Encoding": encoding})


# ── compression ────────────────────────────────────────────────

def test_html_is_compressed_and_much_smaller():
    plain = get("/", encoding="identity")
    assert plain.headers.get("Content-Encoding") is None
    for encoding in ("br", "gzip"):
        r = get("/", encoding=encoding)
        assert r.headers["Content-Encoding"] == encoding, encoding
        # The document was 92 KB on the wire. Anything under half
        # would still be a regression worth catching.
        assert len(r.data) < len(plain.data) / 3, encoding


def test_css_and_js_are_compressed():
    for path in ("/static/css/style.css?v=1",
                 "/static/js/bundle/index.js?v=1"):
        assert get(path).headers.get("Content-Encoding") == "br", path


def test_brotli_is_preferred_when_the_client_takes_both():
    # br beats gzip on text of this size, and every current browser
    # sends both.
    assert get("/", "gzip, br").headers["Content-Encoding"] == "br"


def test_a_client_that_asks_for_nothing_gets_identity():
    r = get("/", encoding="identity")
    assert r.status_code == 200
    assert b"<html" in r.data


def test_vary_keeps_cookie_after_compression_added_its_own():
    """Flask-Compress adds Accept-Encoding to the same header.

    A plain assignment on either side would drop the other's tokens,
    and losing Cookie would let a shared cache hand one visitor's
    language to another."""
    vary = get("/").headers["Vary"]
    tokens = {v.strip() for v in vary.split(",")}
    assert {"Cookie", "Sec-Fetch-Site", "Accept-Encoding"} <= tokens


# ── caching ────────────────────────────────────────────────────

def test_html_revalidates_instead_of_never_caching():
    for path in ("/", "/en", "/loans", "/en/loans"):
        assert (get(path).headers["Cache-Control"]
                == "public, max-age=0, must-revalidate"), path


def test_fingerprinted_static_is_immutable_for_a_year():
    # ?v= is the fingerprint: it changes whenever any asset does, so
    # the bytes behind one of these URLs never change.
    r = get("/static/js/bundle/index.js?v=123")
    assert r.headers["Cache-Control"] == \
        "public, max-age=31536000, immutable"


def test_unversioned_static_is_not_immutable():
    """The vendored Chart.js and the favicons carry no ?v=, so a
    year of immutable caching would strand a fix behind a URL nobody
    can bust."""
    r = get("/static/js/vendor/chart.umd.min.js")
    assert "immutable" not in r.headers["Cache-Control"]
    assert r.headers["Cache-Control"] == "public, max-age=3600"


def test_the_pdf_export_still_refuses_to_be_cached():
    # A generated report belongs to the visitor who asked for it.
    source = open(os.path.join(os.path.dirname(__file__), "..",
                               "app.py")).read()
    export = source[source.index("def export_pdf"):]
    assert 'Cache-Control"] = "no-store"' in export


# ── robots.txt ─────────────────────────────────────────────────

def test_robots_allows_all_and_points_at_the_sitemap():
    r = get("/robots.txt", "identity")
    assert r.status_code == 200
    assert r.mimetype == "text/plain"
    body = r.data.decode()
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Sitemap: https://pension.oats.lv/sitemap.xml" in body


# ── sitemap.xml ────────────────────────────────────────────────

def _entries():
    """Every <url> as {loc: {hreflang: href}}. Parsed as real XML: the
    input is this app's own response, not third-party data."""
    # identity: the body is brotli by default, and .data is raw.
    root = ET.fromstring(get("/sitemap.xml", "identity").data.decode())
    return {u.find(f"{SITEMAP_NS}loc").text:
            {a.get("hreflang"): a.get("href") for a in u.findall(XHTML)}
            for u in root.findall(f"{SITEMAP_NS}url")}


def test_sitemap_serves_and_lists_both_trees():
    r = get("/sitemap.xml", "identity")
    assert r.status_code == 200
    assert r.mimetype == "application/xml"
    assert set(_entries()) == {
        "https://pension.oats.lv/",
        "https://pension.oats.lv/en",
        "https://pension.oats.lv/loans",
        "https://pension.oats.lv/en/loans",
    }


def test_every_url_is_annotated_with_its_language_pair():
    for loc, alts in _entries().items():
        assert set(alts) == {"lv", "en", "x-default"}, loc
        assert alts["x-default"] == alts["lv"], loc
        assert loc in (alts["lv"], alts["en"]), loc


def test_sitemap_agrees_with_the_hreflang_in_the_markup():
    """A sitemap that contradicts the page's own head is worse than
    one that stays silent: the two are competing claims about the
    same pair, and a crawler discards both."""
    for loc, alts in _entries().items():
        path = loc.removeprefix("https://pension.oats.lv") or "/"
        body = get(path, "identity").data.decode()
        head = dict(re.findall(
            r'<link rel="alternate" hreflang="([^"]+)"\s*\n?\s*'
            r'href="([^"]+)" />', body))
        assert head == alts, (loc, head, alts)


def test_lastmod_is_the_curated_date_not_today():
    """Today's date would tell a crawler these pages change daily.
    They change when the rates are rechecked, which is what the
    footer already shows."""
    from data import DATA_UPDATED
    body = get("/sitemap.xml", "identity").data.decode()
    assert body.count(f"<lastmod>{DATA_UPDATED}</lastmod>") == 4
    assert re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", body)


def test_every_listed_url_actually_answers_200():
    for loc in _entries():
        path = loc.removeprefix("https://pension.oats.lv") or "/"
        assert get(path).status_code == 200, loc


# ── the JS bundle ──────────────────────────────────────────────

def test_the_entry_imports_exactly_what_the_fallback_lists():
    """entry.index.js and app.INDEX_MODULES are the same list twice.

    If they drift, the bundle and the no-bundle fallback load
    different code and only one of them gets tested."""
    entry = open(os.path.join(os.path.dirname(__file__), "..",
                              "static", "js", "entry.index.js")).read()
    imported = re.findall(r'import "\./(\w+)\.js";', entry)
    assert imported == delivery.INDEX_MODULES


def test_the_page_loads_the_bundle_when_one_is_built():
    body = get("/", "identity").data.decode()
    if not os.path.exists(os.path.join(app.static_folder, "js",
                                       "bundle", "index.js")):
        return                       # no build present, fallback path
    assert "js/bundle/index.js" in body
    # And not the modules it replaced.
    for name in delivery.INDEX_MODULES:
        assert f"js/{name}.js?" not in body, name


def test_the_seo_paths_derive_their_english_twins():
    # Listed once, in Latvian; the English half is computed, so the
    # two cannot drift apart.
    assert seo.en_path("/") == "/en"
    assert seo.en_path("/loans") == "/en/loans"
