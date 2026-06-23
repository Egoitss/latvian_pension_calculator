"""
Runtime i18n for the pension simulator.

English source strings are the keys; Latvian overrides live in
translations/lv.yaml (English text -> Latvian text). The t() helper
returns the override when lang == "lv", else the English source, so
any unwrapped or untranslated string safely falls back to English.

Mirrors the HOME_PAGE method: English is the source of truth, the
LV catalog only carries overrides.
"""
from __future__ import annotations

from pathlib import Path

import yaml

LANGS = ("en", "lv")
_ROOT = Path(__file__).parent
_CATALOG: dict[str, dict[str, str]] = {}


def _load(lang: str) -> dict[str, str]:
    # Load (and cache) the override catalog for one language.
    if lang in _CATALOG:
        return _CATALOG[lang]
    path = _ROOT / "translations" / f"{lang}.yaml"
    data: dict[str, str] = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _CATALOG[lang] = data
    return data


def lang_from_path(path: str) -> str:
    # "/lv" or "/lv/..." selects Latvian; everything else English.
    return "lv" if path == "/lv" or path.startswith("/lv/") else "en"


def _norm(text: str) -> str:
    # Collapse any internal whitespace/newlines (templates may wrap a
    # key across lines) so lookups match the normalized catalog keys.
    return " ".join(text.split())


def make_t(lang: str):
    # Return a t(text) closure bound to one request's language.
    overrides = _load(lang) if lang != "en" else {}

    def t(text: str) -> str:
        if lang == "en":
            return text
        key = _norm(text)
        return overrides.get(key, text)

    return t


def js_catalog(lang: str) -> dict[str, str]:
    # The override map handed to the browser for JS-side strings.
    return _load(lang) if lang != "en" else {}
