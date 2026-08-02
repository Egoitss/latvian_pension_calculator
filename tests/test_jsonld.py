"""The structured data must describe the page it ships on.

A block is a machine-readable claim, so these check the two ways it
can be wrong: saying something untrue, and saying it on a page where
it does not apply.
"""
from __future__ import annotations

import html
import json
import re

import jsonld
from app import app

BLOCK = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _blocks(path):
    """Every JSON-LD block on a page, keyed by @type."""
    body = app.test_client().get(path).data.decode()
    return {json.loads(b)["@type"]: json.loads(b)
            for b in BLOCK.findall(body)}


def test_the_simulator_declares_one_web_application():
    for path in ("/", "/en"):
        assert set(_blocks(path)) == {"WebApplication"}, path


def test_the_loan_calculator_declares_nothing_yet():
    """A separate tool with no description of its own. Silence beats
    a block copied from the simulator, which would describe the wrong
    page."""
    for path in ("/loans", "/en/loans"):
        assert _blocks(path) == {}, path


def test_no_faqpage_anywhere():
    """FAQPage is a claim that the questions are on the page. There is
    no FAQ on this site, so no page may declare one."""
    for path in ("/", "/en", "/loans", "/en/loans"):
        assert "FAQPage" not in _blocks(path), path


def test_the_application_matches_the_page_it_ships_on():
    for path, lang in (("/", "lv"), ("/en", "en")):
        body = app.test_client().get(path).data.decode()
        app_block = _blocks(path)["WebApplication"]
        assert app_block["url"] == f"https://pension.oats.lv{path}"
        assert app_block["inLanguage"] == lang
        # The name and description are the page's own title and meta
        # description, not a second pair written for the crawler.
        # The markup carries the HTML-escaped form of the same text;
        # the JSON-LD carries it raw, which is correct for both.
        assert f"<title>{html.escape(app_block['name'])}" in body
        assert (f'<meta name="description" content='
                f'"{html.escape(app_block["description"])}"') in body


def test_the_simulator_is_declared_free_because_it_is():
    block = _blocks("/")["WebApplication"]
    assert block["isAccessibleForFree"] is True
    assert block["offers"]["price"] == "0"
    assert block["offers"]["priceCurrency"] == "EUR"
    assert block["applicationCategory"] == "FinanceApplication"


def test_the_publisher_states_only_what_is_registered():
    """40203754767 is the commercial register number, not a VAT code."""
    pub = _blocks("/")["WebApplication"]["publisher"]
    assert pub["name"] == 'SIA "OATS"'
    assert pub["identifier"]["value"] == "40203754767"
    assert "vatID" not in pub and "taxID" not in pub


def test_a_block_cannot_break_out_of_its_script_tag():
    body = app.test_client().get("/").data.decode()
    for block in BLOCK.findall(body):
        assert "<" not in block
    assert "<" not in jsonld.to_script({"name": "</script><img src=x>"})
