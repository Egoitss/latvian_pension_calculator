"""The ⓘ footnote disclosure and the survival chip grid.

Five statistical sources (salary growth, inflation, indexation, P2L
history, property appreciation) used to sit permanently under their
fields as small grey text, and the survival odds as one wrapping line of
"label: value" pairs. On a phone that pushed the sliders they described
below the fold. What these guard is that the sources stay reachable and
that the JS still finds the elements it writes into.
"""
from __future__ import annotations

import re

from app import app

NOTE_IDS = {"note-salary", "note-inflation", "note-indexation",
            "note-p2l", "note-property"}
# static/js/*.js writes the survival percentages into these.
SURVIVAL_IDS = ("survivalToPension", "survivalAt5",
                "survivalAt10", "survivalPct")


def _page(path: str = "/") -> str:
    return app.test_client().get(path).data.decode()


def _css() -> str:
    return open("static/css/pc-info.css").read()


def _block(selector: str) -> str:
    """The declarations of one rule, for asserting exact spec values."""
    css = _css()
    start = css.index(selector + " {") + len(selector) + 2
    return css[start:css.index("}", start)]


# ---- the disclosure -------------------------------------------------

def test_every_footnote_is_behind_a_button():
    html = _page()
    controls = set(re.findall(r'aria-controls="(note-[\w-]+)"', html))
    assert controls == NOTE_IDS


def test_each_button_points_at_a_panel_that_exists():
    html = _page()
    panels = set(re.findall(r'class="pc-note" id="(note-[\w-]+)"', html))
    assert panels == NOTE_IDS


def test_panels_are_collapsed_until_asked_for():
    html = _page()
    assert html.count('data-open="false"') == len(NOTE_IDS)
    assert 'aria-expanded="true"' not in html
    # height:0 is what makes it collapsed; a missing rule would leave
    # every source expanded and the change would be invisible.
    assert "height: 0;" in _block(".pc-note")
    assert "overflow: hidden;" in _block(".pc-note")


def test_the_tap_target_is_44px_around_an_18px_icon():
    block = _block(".pc-info")
    assert "width: 44px;" in block
    assert "height: 44px;" in block
    assert "width: 18px; height: 18px;" in _block(".pc-info svg")
    # The row must not grow to 44px; the target overhangs it instead.
    assert "margin: -13px 0 -13px -12px;" in block


def test_the_button_carries_a_label_for_screen_readers():
    html = _page()
    assert html.count('class="pc-info" aria-expanded') == len(NOTE_IDS)
    assert "Uz kā tas balstās" in html                  # LV default
    assert "What this is based on" in _page("/en")


def test_the_note_keeps_its_source_text():
    """The point of the change is to move the sources, not drop them."""
    html = _page("/en")
    for fragment in ("CSB stat.gov.lv", "CSP/Eurostat", "workforce shrinking",
                     "manapensija.lv", "Arco Real Estate"):
        assert fragment in html, fragment


def test_the_property_note_keeps_the_id_its_script_writes_to():
    """static/js/property.js restates the rate for the selected scenario
    with g("propRateNote").textContent, which throws on a missing
    element and would take setLocType down with it."""
    html = _page()
    assert 'class="pc-note-in" id="propRateNote"' in html


def test_the_animation_matches_the_spec():
    assert "transition: height 150ms ease" in _block(".pc-note")
    inner = _block(".pc-note-in")
    assert "padding: 8px 12px;" in inner
    assert "border-radius: 8px;" in inner
    assert "font-size: 12px;" in inner


def test_the_toggle_script_is_loaded():
    # CSP here is script-src 'self', so it has to be a vendored file.
    # info.js reaches the page inside the bundle now, or through the
    # no-bundle fallback; either way it is in the one list that
    # decides what the simulator page loads.
    import delivery
    assert "info" in delivery.INDEX_MODULES
    assert "pc-info.css" in open("templates/base.html").read()


# ---- the survival chips ---------------------------------------------

def test_the_survival_ids_survive_the_rewrite():
    """These are the JS contract. Renaming one silently blanks a chip."""
    html = _page()
    for chip_id in SURVIVAL_IDS:
        assert f'id="{chip_id}"' in html, chip_id


def test_there_are_four_chips_in_two_columns():
    assert _page().count('class="pc-chip"') == 4
    grid = _block(".pc-chips")
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in grid
    assert "gap: 8px;" in grid


def test_chip_typography_matches_the_spec():
    label = _block(".pc-chip-lbl")
    assert "font-size: 11px;" in label
    assert "text-transform: uppercase;" in label
    value = _block(".pc-chip-val")
    assert "font-size: 16px;" in value
    assert "font-weight: 500;" in value
    assert "padding: 10px 12px;" in _block(".pc-chip")


def test_the_chips_read_in_latvian():
    html = _page()
    for label in ("Sasniegt pensiju", "+5 g.", "+10 g.", "Izmaksas beigas"):
        assert label in html, label
    # The old inline run put a colon after each label; the chips do not.
    assert "Sasniegt pensiju:" not in html
