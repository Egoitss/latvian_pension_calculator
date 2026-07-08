# Changelog

All notable changes to the pension calculator (**pension.oats.lv**) are
recorded here. Format follows [Keep a Changelog]; versions follow
[SemVer].

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[SemVer]: https://semver.org/

## [1.0.0] — 2026-07-08

First tagged release. Prior history predates versioning.

### Changed
- Replacement rate is now a true **gross/gross** metric (OECD-style):
  gross pension ÷ gross salary at retirement. The numerator switched
  from a mixed basis (pre-tax P1 + after-tax P2/P3) to all pre-tax —
  P1 (pre-tax) + P2 pre-tax annuity + P3 pre-gains-tax drawdown — sent
  as a new `grossMonthly` field. The denominator was already gross.
  Applied consistently to the report headline, per-scenario cards, and
  the AI-review band so they never diverge. On-screen take-home stays
  net; only the percentage changed (it rises ~5–8 points).

### Notes
- Backward-compatible: falls back to the net total for payloads that
  don't carry `grossMonthly`.
