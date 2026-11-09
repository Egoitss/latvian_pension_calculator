"""The OATS mark comes from the shared macro file in oats-scan.

templates/_oat_mark.html and the icon files in static/ are byte copies
of the masters in oats-scan/handoff/logo/. These tests skip when that
sibling checkout is absent and fail on drift when it is present. The
PDF report must draw the mark through the same macro, never inline.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from i18n import make_t  # noqa: E402
from report_pdf import render_report_html  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT.parent / "oats-scan" / "handoff" / "logo"
STEM_PATH = "M48 14H52V90H48Z"
# Local file beside the handoff master it must equal byte for byte.
BRAND_PAIRS = [
    (ROOT / "templates" / "_oat_mark.html", "_oat_mark.html"),
    (ROOT / "static" / "favicon-16.png", "oats-mark-16.png"),
    (ROOT / "static" / "favicon-32.png", "oats-mark-32.png"),
    (ROOT / "static" / "favicon-96.png", "oats-mark-96.png"),
    (ROOT / "static" / "favicon-192.png", "oats-mark-192.png"),
    (ROOT / "static" / "apple-touch-icon.png", "oats-mark-180.png"),
    (ROOT / "static" / "favicon.svg", "oats-mark.svg"),
]
needs_handoff = pytest.mark.skipif(
    not HANDOFF.is_dir(),
    reason="oats-scan/handoff/logo not checked out beside this repo")


@needs_handoff
@pytest.mark.parametrize("local, master", BRAND_PAIRS,
                         ids=[pair[1] for pair in BRAND_PAIRS])
def test_brand_files_equal_the_handoff_masters(local, master):
    """The macro copy and every icon equal the oats-scan handoff file."""
    assert local.read_bytes() == (HANDOFF / master).read_bytes()


def test_pdf_report_draws_the_mark_through_the_macro():
    """The PDF brand block holds the macro's mark, not an inline copy."""
    html = render_report_html({}, make_t("en"), "2026-06-18")
    brand = html.split('<div class="brand">', 1)[1].split("</div>", 1)[0]
    assert STEM_PATH in brand
    # The macro's square takes currentColor; a fixed fill means an
    # inline copy of the drawing has crept back in.
    assert 'fill="currentColor"' in brand
    assert "#14110E" not in brand
    assert "<circle" not in brand
