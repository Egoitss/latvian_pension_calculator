"""The drawer covers the sticky result bar.

The bar is fixed to the bottom of every page and carries the "Download
report PDF" button. It sat at z-index 100 while the drawer's backdrop
was at 60, so opening the menu dimmed the page but left that button
painted on top of the dim and still tappable.

Layering now comes from one scale declared in the shared o-header.css:
fixed chrome 40, backdrop 50, panel 60.
"""
from __future__ import annotations

import re

from app import app

THEME = "static/css/oats-theme.css"
SHARED = "static/css/o-header.css"


def _page(path: str = "/") -> str:
    return app.test_client().get(path).data.decode()


def _rule(css: str, selector: str) -> str:
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if selector in [s.strip() for s in block.group(1).split(",")]:
            return block.group(2)
    raise AssertionError(f"no rule for {selector}")


def test_the_bar_takes_its_layer_from_the_shared_scale():
    theme = open(THEME).read()
    bar = _rule(theme, ".mobile-bar")
    assert "z-index: var(--z-bar);" in bar
    # The literal that caused the bug must not come back.
    assert "z-index: 100" not in bar


def test_the_scale_is_defined_once_and_shipped():
    """It lives in o-header.css, which every property serves; the theme
    only consumes it."""
    shared = open(SHARED).read()
    for token in ("--z-bar: 40;", "--z-drawer-backdrop: 50;", "--z-drawer: 60;"):
        assert token in shared, token
    assert "--z-bar:" not in open(THEME).read(), "scale must not be redefined"


def test_the_bar_is_tagged_for_the_drawer_to_hide():
    html = _page()
    assert re.search(r'class="mobile-bar[^"]*\bo-bar\b', html)
    assert "visibility: hidden;" in _rule(
        open(SHARED).read(), "body.o-drawer-open .o-bar")


def test_the_bar_is_hidden_even_without_the_shared_hook():
    """Three independent guards, because this is the one element that can
    reach over an open drawer and it carries the download button: the
    z-index keeps it under the backdrop, the shared
    body.o-drawer-open .o-bar rule hides it, and this one repeats the
    hide without depending on a page remembering the o-bar class.

    Hiding the whole bar rather than .mb-desktop and .mb-right in turn
    means a child added later is covered from the day it appears.
    """
    theme = open(THEME).read()
    assert "visibility: hidden;" in _rule(theme, "body.o-drawer-open .mobile-bar")


def test_the_shared_sheet_loads_before_the_theme():
    """Both set z-index at the same specificity, so the theme has to be
    able to override; the scale itself is custom properties, which
    cascade regardless of order."""
    base = open("templates/base.html").read()
    assert base.index("o-header.css") < base.index("oats-theme.css")


def test_nothing_on_the_page_outranks_the_drawer_by_accident():
    """The two deliberate exceptions are the skip link (100) and the
    copy toast (110); both must clear an open drawer. Any other value
    above 60 would put page furniture over the backdrop."""
    theme = open(THEME).read()
    above = [int(n) for n in re.findall(r"z-index:\s*(\d+)", theme) if int(n) > 60]
    assert above == [100], above          # .c-skip only
    html = _page()
    tailwind = {m for m in re.findall(r"z-\[(\d+)\]", html)}
    assert tailwind <= {"110"}, tailwind  # #copyFeedback only
