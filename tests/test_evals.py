import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evals import graders
from evals.cases import CASES
import ai_review


def _f(band="WEAK", heavy=False, prop=0, size=0, real=560, nominal=2800):
    return {"band": band, "heavy": heavy, "prop": prop, "size": size,
            "real": real, "nominal": nominal}


# ── relocation guardrail ───────────────────────────────────────

def test_relocation_blocked_in_non_weak():
    s, _ = graders.grade_relocation(
        "Consider relocating to a cheaper country.", _f(band="STRONG"),
        "en")
    assert s == graders.FAIL


def test_relocation_allowed_in_weak():
    s, _ = graders.grade_relocation(
        "As a last resort, relocate abroad.", _f(band="WEAK"), "en")
    assert s == graders.PASS


def test_relocation_clean_non_weak_passes():
    s, _ = graders.grade_relocation(
        "Raise 3rd-pillar contributions.", _f(band="STRONG"), "en")
    assert s == graders.PASS


# ── phantom property + downsizing ──────────────────────────────

def test_no_phantom_property_flags_invented_advice():
    s, _ = graders.grade_no_phantom(
        "You should downsize your home.", _f(prop=0, size=0), "en")
    assert s == graders.FAIL


def test_downsize_required_when_oversized():
    s, _ = graders.grade_downsize(
        "Keep everything as is.", _f(heavy=True, prop=300000), "en")
    assert s == graders.FAIL


def test_no_downsize_when_rightsized():
    # Home suits a couple (size given, not oversized) → no downsizing.
    bad, _ = graders.grade_no_downsize_rightsized(
        "Consider downsizing your home.", _f(size=60, heavy=False), "en")
    assert bad == graders.FAIL
    ok, _ = graders.grade_no_downsize_rightsized(
        "Raise 3rd-pillar contributions.", _f(size=60, heavy=False), "en")
    assert ok == graders.PASS


def test_downsize_optional_when_strong():
    # Oversized but STRONG → downsizing is optional, absence is fine.
    s, _ = graders.grade_downsize(
        "Keep everything as is.",
        _f(band="STRONG", heavy=True, prop=300000), "en")
    assert s == graders.SKIP


def test_no_overadvice_flags_downsize_at_excellent():
    # The regression: pushing downsizing at EXCELLENT is a failure.
    s, _ = graders.grade_no_overadvice(
        "Consider downsizing your home.",
        _f(band="EXCELLENT", heavy=True, prop=300000), "en")
    assert s == graders.FAIL


def test_no_overadvice_clean_at_strong_passes():
    s, _ = graders.grade_no_overadvice(
        "Your pension is on track.", _f(band="STRONG"), "en")
    assert s == graders.PASS


# ── format + language ──────────────────────────────────────────

def test_markdown_detected():
    assert graders.grade_no_markdown("**Verdict:** weak", _f(), "en")[0] \
        == graders.FAIL


def test_truncation_detected():
    assert graders.grade_not_truncated("relocating uz val", _f(), "lv")[0] \
        == graders.FAIL


def test_language_mismatch_detected():
    s, _ = graders.grade_language("Pārcelšanās uz ārzemēm.", _f(), "en")
    assert s == graders.FAIL


def test_lv_language_ok():
    s, _ = graders.grade_language("Jūsu pensija ir vāja.", _f(), "lv")
    assert s == graders.PASS


# ── case set sanity ────────────────────────────────────────────

def test_cases_have_derivable_facts():
    assert len(CASES) >= 12
    for c in CASES:
        facts = ai_review._facts(c["data"])
        assert facts["band"] in {
            "WEAK", "MODERATE", "STRONG", "EXCELLENT"}
        assert c["lang"] in {"en", "lv"}
