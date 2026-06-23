# AI-review prompt evaluation

Measures the DeepSeek AI-review prompt in `ai_review.py` against
defined success criteria, following Anthropic's
"define success criteria → build evals → grade" loop.

## Success criteria

The review is a short pension verdict shown in the PDF. Most
requirements are rule-like, so they are **code-graded** (the fastest,
most reliable tier). Expected behaviour per case is **derived** from
`ai_review._facts`, so the eval stays in sync with the scoring logic.

| Criterion | What it checks | Target |
| --- | --- | --- |
| Band verdict | Verdict reflects the rate band (WEAK/MOD/STRONG/EXC) | ≥ 90% |
| Relocation gating | Relocation mentioned **only** when WEAK (guardrail) | 100% |
| 3rd-pillar rec | Recommends voluntary 3rd-pillar (priority #1) | ≥ 95% |
| Downsize oversized | Suggests downsizing an oversized home | ≥ 90% |
| No phantom property | No downsizing advice when no property entered | 100% |
| Size / occupancy | References size/residents when home is oversized | ≥ 90% |
| Inflation note | Flags inflation when purchasing power drops materially | ≥ 85% |
| Weak living-cost | Flags Latvian living-cost shortfall when WEAK | ≥ 90% |
| Language | Output is in the requested language (EN/LV) | 100% |
| No markdown | Plain text only (no `**`, headers, backticks) | 100% |
| Not truncated | Ends on terminal punctuation | 100% |
| Length | ≤ ~80 words (2–3 short sentences) | ≥ 90% |

Operational targets: **latency** p-max < 8 s (the API timeout);
**cost** ≈ $0.0003 per report (deepseek-chat).

The **relocation gating** and **no phantom property** criteria are
"egregious error" guardrails — a single violation is a real failure,
hence the 100% target.

## Test set

`cases.py` covers the band × property × language matrix plus edge
cases (empty payload, totals-only fallback). Grow it by adding to
`CASES`; expectations are derived automatically.

## Run

The eval calls the **real DeepSeek API** once per case, so it is **not**
part of the pytest suite. Run on demand:

```bash
source .venv/bin/activate
export DEEPSEEK_API_KEY=...        # or rely on .env
python -m evals.run_eval
```

The grading logic itself is unit-tested offline in
`tests/test_evals.py` (no network), so the graders stay trustworthy.

## Iterate

Read the failure list, spot patterns, adjust the prompt in
`ai_review.py`, and re-run. That is the prompt-engineering loop.
