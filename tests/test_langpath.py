"""Cross-subdomain language cookie and the hreflang set.

Routing here was already path-based (Latvian bare, English under /en);
these guard the parts PROMPT 03 added.
"""
from __future__ import annotations

import re

from app import app


def _client():
    return app.test_client()


def test_page_records_its_language_in_the_cookie():
    c = _client()
    for path, want in (("/", "lv"), ("/en", "en"),
                       ("/loans", "lv"), ("/en/loans", "en")):
        c.set_cookie("oats_lang", "")
        jar = c.get(path).headers.get("Set-Cookie", "")
        assert f"oats_lang={want}" in jar, path
        # RFC 6265 drops the leading dot; oats.lv already covers every
        # subdomain under it.
        assert "Domain=oats.lv" in jar
        assert "Max-Age=31536000" in jar          # one year
        assert "SameSite=Lax" in jar


def test_stored_english_moves_a_visitor_arriving_at_the_root():
    c = _client()
    c.set_cookie("oats_lang", "en")
    r = c.get("/", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 302
    assert r.headers["Location"] == "/en"


def test_the_cookie_never_traps_a_visitor_in_english():
    # The LV switcher points at "/". Bouncing that back to /en would
    # leave no way home.
    c = _client()
    c.set_cookie("oats_lang", "en")
    assert c.get("/", headers={"Sec-Fetch-Site": "same-origin"}
                 ).status_code == 200


def test_only_the_root_consults_the_cookie():
    c = _client()
    c.set_cookie("oats_lang", "en")
    r = c.get("/loans", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 200


def test_responses_vary_on_what_they_branch_on():
    vary = _client().get("/").headers.get("Vary", "")
    assert "Cookie" in vary and "Sec-Fetch-Site" in vary


def test_legacy_lv_paths_still_redirect():
    c = _client()
    assert c.get("/lv").headers["Location"] == "/"
    assert c.get("/lv/loans").headers["Location"] == "/loans"


def test_every_page_declares_the_full_hreflang_set():
    pat = re.compile(
        r'<link rel="alternate" hreflang="([^"]+)"\s*href="([^"]+)"', re.S)
    c = _client()
    for path in ("/", "/en", "/loans", "/en/loans"):
        tags = pat.findall(c.get(path).data.decode())
        assert {k for k, _ in tags} == {"lv", "en", "x-default"}, path
        for _, url in tags:
            assert url.startswith("https://pension.oats.lv"), (path, url)


def test_cross_property_links_use_path_prefixes():
    c = _client()
    for path in ("/", "/en"):
        html = c.get(path).data.decode()
        assert "lang=en" not in html, path
        assert "/tame/en" not in html, path
