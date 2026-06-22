# run_eval.py — score the AI-review prompt against the success
# criteria. Calls the real DeepSeek API once per case, so run it on
# demand (NOT in the pytest suite):  python -m evals.run_eval
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ai_review                       # noqa: E402
from evals import graders             # noqa: E402
from evals.cases import CASES         # noqa: E402

# (label, grader, target%) — targets from evals/README.md.
CRITERIA = [
    ("band verdict", graders.grade_band, 90),
    ("relocation gating", graders.grade_relocation, 100),
    ("3rd-pillar rec", graders.grade_pillar3, 95),
    ("downsize oversized", graders.grade_downsize, 90),
    ("no phantom property", graders.grade_no_phantom, 100),
    ("size/occupancy", graders.grade_size, 90),
    ("inflation note", graders.grade_inflation, 85),
    ("weak living-cost", graders.grade_living, 90),
    ("language", graders.grade_language, 100),
    ("no markdown", graders.grade_no_markdown, 100),
    ("not truncated", graders.grade_not_truncated, 100),
    ("length <= 80w", graders.grade_length, 90),
]
_COST_PER_CALL = 0.0003                # rough deepseek-chat estimate


def _grade_one(out, facts, lang, tally, fails, case_id):
    for label, fn, _ in CRITERIA:
        status, note = fn(out, facts, lang)
        tally[label][status] += 1
        if status == graders.FAIL:
            fails.append((case_id, label, note))


def run():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY not set — cannot run the eval.")
        return
    tally = {l: {"pass": 0, "fail": 0, "skip": 0} for l, _, _ in CRITERIA}
    fails, lat, errors = [], [], 0
    for c in CASES:
        facts = ai_review._facts(c["data"])
        t0 = time.time()
        out = ai_review.generate_review(c["data"], c["lang"])
        lat.append(time.time() - t0)
        if not out:
            errors += 1
            fails.append((c["id"], "GENERATION", "no output"))
            continue
        _grade_one(out, facts, c["lang"], tally, fails, c["id"])
    _report(tally, fails, lat, len(CASES), errors)


def _report(tally, fails, lat, n, errors):
    print(f"\nAI-review prompt eval — {n} cases, {errors} generation "
          f"errors\n" + "=" * 60)
    print(f"{'criterion':<22}{'score':>10}{'target':>9}  result")
    print("-" * 60)
    overall = []
    for label, _, target in CRITERIA:
        t = tally[label]
        graded = t["pass"] + t["fail"]
        if graded == 0:
            print(f"{label:<22}{'n/a':>10}{target:>8}%  (all skipped)")
            continue
        pct = round(t["pass"] / graded * 100)
        overall.append(pct >= target)
        mark = "PASS" if pct >= target else "**MISS**"
        score = f"{t['pass']}/{graded}"
        print(f"{label:<22}{score:>10}{target:>8}%  {pct:>3}% {mark}")
    print("-" * 60)
    met = sum(overall)
    print(f"criteria met: {met}/{len(overall)}")
    if lat:
        print(f"latency: avg {sum(lat)/len(lat):.1f}s  "
              f"max {max(lat):.1f}s")
    print(f"approx cost: ${(n - errors) * _COST_PER_CALL:.4f} "
          f"({n - errors} calls)")
    if fails:
        print("\nfailures:")
        for cid, label, note in fails:
            print(f"  [{cid}] {label}: {note}")


if __name__ == "__main__":
    run()
