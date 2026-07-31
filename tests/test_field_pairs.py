"""Side-by-side input pairs share a baseline.

Each pair was laid out with flex and per-field widths, and the label sat
above the input on a plain margin. When one label wrapped to two lines
and its partner did not, the inputs ended on different baselines. Latvian
and English wrap at different widths, so a pair that looked right in one
language stepped in the other.

The geometry is asserted in the browser; what these guard is the
contract that pass depended on, so a later edit cannot quietly undo it.
"""
from __future__ import annotations

import re

from app import app

# Both halves visible: these are the ones that must share a baseline.
VISIBLE_PAIRS = (
    ("p1Capital", "p1RecordYears"),
    ("p3Balance", "p3Monthly"),
    ("propPrice", "propSize"),
)
# Present in the DOM but display:none — they carry a stored value only.
VALUE_ONLY = ("p1RecordMonths", "p2AlreadyEarned")


def _page(path: str = "/") -> str:
    return app.test_client().get(path).data.decode()


def _css() -> str:
    return open("static/css/pc-fields.css").read()


def _rule(selector: str) -> str:
    """Declarations of the rule whose selector list contains `selector`.

    Several rules here group selectors (".pc-field input, .pc-field
    select"), so matching on "<selector> {" alone would miss them.
    """
    css = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    # Drop the @media wrapper so its inner rules scan like the rest.
    css = re.sub(r"@media[^{]*\{", "", css)
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        names = [s.strip() for s in block.group(1).split(",")]
        if selector in names:
            return block.group(2)
    raise AssertionError(f"no rule for {selector}")


def _classes(html: str, name: str) -> int:
    """How many elements carry `name` in their class attribute.

    Counting the bare string would also catch it in HTML comments.
    """
    return sum(name in attr.split()
               for attr in re.findall(r'class="([^"]*)"', html))


def _field_of(html: str, input_id: str) -> str:
    """The markup from the enclosing pc-field open tag to the input."""
    at = html.index(f'id="{input_id}"')
    start = html.rindex('<div class="pc-field"', 0, at)
    return html[start:at]


# ---- the grid --------------------------------------------------------

def test_the_pair_is_a_two_column_grid():
    rule = _rule(".pc-pair")
    assert "display: grid;" in rule
    assert "grid-template-columns: 1fr 1fr;" in rule
    assert "column-gap: 16px;" in rule
    assert "align-items: stretch;" in rule


def test_the_pair_stacks_below_400px():
    css = _css()
    block = css[css.index("@media (max-width: 399.98px)"):]
    assert "grid-template-columns: 1fr;" in block
    assert "row-gap" in block


def test_each_field_is_a_flex_column():
    rule = _rule(".pc-field")
    assert "display: flex;" in rule
    assert "flex-direction: column;" in rule
    assert "gap: 6px;" in rule


def test_the_input_is_pushed_to_the_bottom():
    """margin-top:auto is what puts both inputs on one baseline: the
    slack collects above the input, not below the shorter label."""
    rule = _rule(".pc-field input")
    assert "margin-top: auto;" in rule
    assert "width: 100%;" in rule
    assert "height: 48px;" in rule
    # 16px is also the point below which iOS Safari zooms on focus.
    assert "font-size: 16px;" in rule


def test_labels_are_capped_at_two_lines():
    rule = _rule(".pc-field > label")
    assert "-webkit-line-clamp: 2;" in rule
    assert "overflow: hidden;" in rule


def test_utility_margins_are_neutralised_inside_a_field():
    """space-y-* and mb-1 are still on these elements; left alone they
    stack with the flex gap and reintroduce the mismatch."""
    rule = _rule(".pc-field > *")
    assert "margin-top: 0;" in rule
    assert "margin-bottom: 0;" in rule


# ---- the markup ------------------------------------------------------

def test_every_visible_pair_uses_the_component():
    html = _page()
    for a, b in VISIBLE_PAIRS:
        for input_id in (a, b):
            assert 'class="pc-field"' in _field_of(html, input_id), input_id


def test_both_halves_of_a_pair_share_one_grid():
    """Same parent, or the grid cannot align them."""
    html = _page()
    for a, b in VISIBLE_PAIRS:
        start = html.index('class="pc-pair"')
        # The two inputs must appear after some pc-pair and before the
        # next one opens.
        ia, ib = html.index(f'id="{a}"'), html.index(f'id="{b}"')
        between = html[min(ia, ib):max(ia, ib)]
        assert "pc-pair" not in between, (a, b)
        assert start < min(ia, ib)


def test_the_hidden_halves_stay_hidden():
    """Tailwind's .hidden and .pc-field have equal specificity and this
    stylesheet loads later, so the guard rule has to exist and these
    elements must not carry pc-field."""
    assert "display: none;" in _rule(".pc-field.hidden")
    assert "display: none;" in _rule(".pc-pair > .hidden")
    html = _page()
    for input_id in VALUE_ONLY:
        at = html.index(f'id="{input_id}"')
        # The nearest class attribute before the input that hides it.
        attrs = re.findall(r'class="([^"]*)"', html[:at])
        hiding = [a for a in attrs if "hidden" in a.split()]
        assert hiding, input_id
        # If pc-field were ever added to that wrapper it would win over
        # .hidden on source order, so the two must not share an element.
        assert "pc-field" not in hiding[-1].split(), (input_id, hiding[-1])


def test_the_stylesheet_is_linked():
    assert "pc-fields.css" in open("templates/base.html").read()


def test_the_old_per_field_widths_are_gone():
    """flex-[2] against flex-1, and a fixed w-24 beside a flex-1, were
    what made the columns unequal in the first place."""
    p1 = open("templates/_pension1.html").read()
    assert "flex-[2]" not in p1
    prop = open("templates/_property.html").read()
    pair = prop[prop.index('class="mt-2 pc-pair"'):]
    assert 'class="w-24"' not in pair[:pair.index("</div>\n\n")]


# ---- both locales ----------------------------------------------------

def test_the_pairs_render_in_both_languages():
    for path, sample in (("/", "Uzkrātais kapitāls"), ("/en", "Accumulated capital")):
        html = _page(path)
        assert sample in html, path
        assert _classes(html, "pc-pair") == 3, (path, _classes(html, "pc-pair"))
        # 3 pairs x 2 visible halves, plus the lone 2nd-pillar total.
        assert _classes(html, "pc-field") == 7, (path, _classes(html, "pc-field"))
