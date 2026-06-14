"""
Generate translations/lv.yaml for the pension simulator.

Scans templates/*.html for t("...") / t('...') keys, plus a few keys
passed as Jinja variables (month names), then machine-translates each
English source to Latvian (Google Translate) while protecting brand,
acronym and proper-noun terms. Mirrors the HOME_PAGE method.

Gap-fill by default: existing curated lv.yaml values are kept; only
missing keys are translated. Use --force to retranslate everything.

Usage:
    python make_lv.py          # gap-fill missing keys
    python make_lv.py --force  # retranslate all
    python make_lv.py --dry    # list keys, write nothing
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import yaml
from deep_translator import GoogleTranslator

ROOT = Path(__file__).parent
TPL = ROOT / "templates"
JS = ROOT / "static" / "js"
DST = ROOT / "translations" / "lv.yaml"

# t("...") and t('...') — capture the key between the quotes.
_KEY_RE = re.compile(r"""\bt\(\s*(["'])(.*?)\1\s*\)""", re.DOTALL)

# Month names are rendered via t(months[i-1]); add them explicitly.
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Terms MT must not translate (protected via placeholders).
KEEP_TERMS = [
    "Claude Sonnet 4.6", "Arco Real Estate", "manapensija.lv",
    "Latvija.lv", "stat.gov.lv", "Eurostat", "EURIBOR", "VSAOI",
    "P2L", "NDC", "CSP", "ECB", "Latio", "IIN", "Riga", "Latvia",
    "Pillar 1", "Pillar 2",
]
_PROT = sorted(KEEP_TERMS, key=len, reverse=True)


def _collect_keys() -> list[str]:
    # Distinct keys from templates AND JS t() calls, first-seen order.
    seen: dict[str, None] = {}
    files = sorted(TPL.glob("*.html")) + sorted(JS.glob("*.js"))
    for f in files:
        if f.name == "i18n.js":          # the helper itself, not UI
            continue
        for _, key in _KEY_RE.findall(f.read_text(encoding="utf-8")):
            key = " ".join(key.split())   # normalize whitespace
            if key:
                seen.setdefault(key, None)
    for m in _MONTHS:
        seen.setdefault(m, None)
    return list(seen)


def _protect(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    for i, term in enumerate(_PROT):
        tok = f"ZZ{i}ZZ"
        pat = r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
        if re.search(pat, text):
            text = re.sub(pat, tok, text)
            mapping[tok] = term
    return text, mapping


def _restore(text: str, mapping: dict[str, str]) -> str:
    for tok, val in mapping.items():
        text = text.replace(tok, val)
    return text


def _house(text: str) -> str:
    # House style (HOME_PAGE): no em-dashes in Latvian.
    text = re.sub(r"\s*—\s*", ", ", text)
    text = re.sub(r"\s+,", ",", text)
    return re.sub(r"  +", " ", text)


def _translate(tr, text, cache):
    if text in cache:
        return cache[text]
    prot, mapping = _protect(text)
    out = tr.translate(prot) or prot
    out = _house(_restore(out, mapping))
    cache[text] = out
    time.sleep(0.2)
    return out


def main() -> None:
    args = sys.argv[1:]
    dry, force = "--dry" in args, "--force" in args
    keys = _collect_keys()
    print(f"{len(keys)} keys collected from templates.")
    existing = {}
    if DST.exists():
        existing = yaml.safe_load(DST.read_text(encoding="utf-8")) or {}
    if dry:
        for k in keys:
            print(f"  {k}")
        return
    tr = GoogleTranslator(source="en", target="lv")
    cache: dict[str, str] = {}
    out: dict[str, str] = {}
    n = 0
    for k in keys:
        if not force and isinstance(existing.get(k), str) \
                and existing[k].strip():
            out[k] = existing[k]
            continue
        out[k] = _translate(tr, k, cache)
        n += 1
    DST.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(out, allow_unicode=True, sort_keys=False,
                          width=72, default_flow_style=False)
    DST.write_text(body, encoding="utf-8")
    print(f"Saved {DST.relative_to(ROOT)} ({n} translated, "
          f"{len(out)} total).")


if __name__ == "__main__":
    main()
