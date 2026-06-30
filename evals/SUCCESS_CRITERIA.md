# AI review — success criteria

What "good" means for the DeepSeek verdict in the PDF report. Each
criterion maps to a grader in `evals/graders.py` and a target in
`evals/run_eval.py`. Run `python -m evals.run_eval` on every prompt
change.

## Feature

A 2-3 sentence Latvian/English verdict on a retirement projection,
grounded ONLY in the supplied facts (no invented numbers), driven by
the replacement-rate band. Rate = nominal pension ÷ gross salary AT
retirement. Bands (anchored to income adequacy — the ~70% "keep your
lifestyle" rule): WEAK <45%, MODERATE 45-60%, STRONG 60-75%,
EXCELLENT ≥75% — the SAME 4 bands the deterministic box uses.

## Criteria

| Dimension | Rule | Grader | Target |
|-----------|------|--------|--------|
| Band fidelity | Verdict names the correct band | `grade_band` | 90% |
| Outlook-aware advice | **STRONG/EXCELLENT get NO corrective advice** (no downsize/sell/relocate/raise) — there is no shortfall | `grade_no_overadvice` | 100% |
| 3rd-pillar (weak/mod) | WEAK/MODERATE recommend raising 3rd-pillar | `grade_pillar3` | 95% |
| Downsizing (weak/mod) | Oversized home → downsize, but only WEAK/MODERATE | `grade_downsize` | 90% |
| No phantom property | No property entered → never mention downsizing | `grade_no_phantom` | 100% |
| Right-sized home | Right-sized → never suggest downsizing | `grade_no_downsize_rightsized` | 100% |
| Relocation guardrail | Relocation only for WEAK, last | `grade_relocation` | 100% |
| Living cost (weak) | WEAK flags the LV cost shortfall | `grade_living` | 90% |
| Inflation | Material erosion → mention inflation | `grade_inflation` | 85% |
| Size reference | Reference m²/occupancy only for weak/mod oversized | `grade_size` | 90% |
| Language | Output matches requested language | `grade_language` | 100% |
| Plain text | No Markdown reaches the PDF | `grade_no_markdown` | 100% |
| Not truncated | Ends on terminal punctuation | `grade_not_truncated` | 100% |
| Length | ≤ 80 words (2-3 sentences) | `grade_length` | 90% |

## Known limits

- The model is non-deterministic (temperature 0.1); a single case may
  flip a 100%-target grader run-to-run. Re-run before treating a lone
  miss as a regression. The `size/occupancy` and `inflation` graders
  are the most variance-prone.
- The denominator (salary at retirement) is computed in
  `insights.salary_at_retirement`: the frontend's `grossAtRetirement`
  if present, else derived from `salaryGrowth` — never today's salary
  (which would inflate the rate).
