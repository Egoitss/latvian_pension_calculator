"""Brand checks: the oat spikelet mark, icon cache version, footer copy.

Guards against the retired ring mark coming back and against dashes
creeping into the footer line, which the site owner bans in prose.
"""
import re

import pytest

from app import app
from i18n import make_t
from report_pdf import render_report_html

STEM_PATH = "M48 14H52V90H48Z"
RING_ARC_MARKERS = ("A26 26", "A12 12", "M76 50A26")
PAGE_PATHS = ["/", "/en", "/loans", "/en/loans"]


def _page(path):
    """Return the rendered HTML of `path` from the Flask test client."""
    return app.test_client().get(path).data.decode()


@pytest.mark.parametrize("path", PAGE_PATHS)
def test_header_carries_oat_mark_and_no_rings(path):
    html = _page(path)
    assert STEM_PATH in html
    assert 'aria-label="OATS"' in html
    assert not any(marker in html for marker in RING_ARC_MARKERS)


def test_pdf_report_carries_oat_mark_and_no_rings():
    html = render_report_html({}, make_t("en"), "2026-06-18")
    assert STEM_PATH in html
    assert 'aria-label="OATS"' in html
    assert not any(marker in html for marker in RING_ARC_MARKERS)


@pytest.mark.parametrize("path", PAGE_PATHS)
def test_icon_links_carry_version_four(path):
    html = _page(path)
    icon_links = re.findall(r'<link rel="(?:icon|apple-touch-icon)"[^>]*>', html)
    assert len(icon_links) == 6
    for link in icon_links:
        assert "?v=4" in link
