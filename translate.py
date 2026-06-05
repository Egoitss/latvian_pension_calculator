"""
Translate Markdown (or plain text) files using Google Translate via deep-translator.

Preserves {{cite:...}} markers and Markdown headings.
Post-processes with an optional terminology glossary.

Usage:
    python translate.py <file.md> [<file2.md> ...]
    python translate.py --dir docs/ --suffix _lv
    python translate.py file.md --to lv --output-dir out/

Install:
    pip install deep-translator click
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import click
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound, NotValidPayload

# ── inlined helpers ────────────────────────────────────────────────────────
_CITE_RE    = re.compile(r"\{\{cite:([^:}]+)(?::([^}]+))?\}\}")
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def _apply_terminology(text: str, terms: dict[str, str]) -> str:
    for src, dst in terms.items():
        text = re.sub(r"\b" + re.escape(src) + r"\b", dst, text)
    return text

# ── terminology glossary (add project-specific overrides here) ─────────────
DEFAULT_TERMINOLOGY: dict[str, str] = {}


# ── translation core ───────────────────────────────────────────────────────
def _extract_placeholders(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    counter = [0]

    def replace(m: re.Match) -> str:
        key = f"CCCITE{counter[0]}CCC"
        placeholders[key] = m.group(0)
        counter[0] += 1
        return key

    return _CITE_RE.sub(replace, text), placeholders


def _restore_placeholders(text: str, placeholders: dict[str, str]) -> str:
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def _safe_translate(translator: GoogleTranslator, text: str) -> str:
    try:
        result = translator.translate(text)
        return result if result else text
    except (TranslationNotFound, NotValidPayload, Exception):
        print("  [warning] Translation failed for paragraph, keeping original.")
        return text


def _translate_paragraph(translator: GoogleTranslator, para: str) -> str:
    para_with_ph, ph = _extract_placeholders(para)
    if len(para_with_ph) <= 4500:
        translated = _safe_translate(translator, para_with_ph)
    else:
        parts = []
        chunk = ""
        for sentence in re.split(r"(?<=[.!?])\s+", para_with_ph):
            if len(chunk) + len(sentence) + 1 > 4500:
                parts.append(_safe_translate(translator, chunk.strip()))
                chunk = sentence
            else:
                chunk = (chunk + " " + sentence).strip()
        if chunk:
            parts.append(_safe_translate(translator, chunk.strip()))
        translated = " ".join(parts)
    return _restore_placeholders(translated or para_with_ph, ph)


def translate_file(
    src_path: Path,
    dst_path: Path | None,
    terminology: dict[str, str] | None = None,
    source_lang: str = "en",
    target_lang: str = "lv",
) -> str:
    text = src_path.read_text(encoding="utf-8")
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    paragraphs = text.split("\n\n")
    translated_paragraphs: list[str] = []

    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if not stripped:
            translated_paragraphs.append("")
            continue

        if _HEADING_RE.match(stripped):
            m = _HEADING_RE.match(stripped)
            hashes = m.group(0)
            heading_text = stripped[m.end():]
            translated_heading = translator.translate(heading_text)
            translated_paragraphs.append(f"{hashes}{translated_heading}")
            time.sleep(0.3)
            continue

        translated = _translate_paragraph(translator, stripped)
        translated_paragraphs.append(translated)
        time.sleep(0.3)
        print(f"  [{src_path.name}] para {i + 1}/{len(paragraphs)} done")

    result = "\n\n".join(translated_paragraphs)
    if terminology:
        result = _apply_terminology(result, terminology)

    if dst_path is not None:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_text(result, encoding="utf-8")
        print(f"Saved: {dst_path} ({len(result.split())} words)")

    return result


# ── CLI ────────────────────────────────────────────────────────────────────
@click.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--dir", "directory", type=click.Path(exists=True, path_type=Path),
              help="Translate all .md files in this directory.")
@click.option("--suffix", default="_lv", show_default=True,
              help="Suffix appended to the output filename (before .md).")
@click.option("--from", "source_lang", default="en", show_default=True,
              help="Source language code.")
@click.option("--to", "target_lang", default="lv", show_default=True,
              help="Target language code.")
@click.option("--no-terminology", is_flag=True,
              help="Skip terminology glossary post-processing.")
@click.option("--output-dir", "output_dir", default=None,
              type=click.Path(path_type=Path),
              help="Directory to write translated files into (default: same as source).")
@click.option("--combine", "combine_name", default=None, metavar="FILENAME",
              help="Merge all translations into one file. Requires --output-dir.")
def translate(
    files: tuple[Path, ...],
    directory: Path | None,
    suffix: str,
    source_lang: str,
    target_lang: str,
    no_terminology: bool,
    output_dir: Path | None,
    combine_name: str | None,
) -> None:
    """Translate Markdown files from English to Latvian (or any language pair)."""
    targets: list[Path] = list(files)
    if directory:
        targets.extend(sorted(directory.glob("*.md")))

    if not targets:
        click.echo("No files to translate. Pass file paths or --dir.", err=True)
        raise SystemExit(1)

    if combine_name and not output_dir:
        click.echo("--combine requires --output-dir.", err=True)
        raise SystemExit(1)

    terminology = None if no_terminology else DEFAULT_TERMINOLOGY or None
    sections: list[str] = []

    for src in targets:
        if src.stem.endswith(suffix.rstrip(".")):
            click.echo(f"Skipping already-translated file: {src.name}")
            continue

        stem = src.stem + suffix
        dst = None if combine_name else (
            (output_dir / f"{stem}.md") if output_dir else src.with_stem(stem)
        )

        click.echo(f"\nTranslating {src.name}…")
        result = translate_file(src, dst, terminology=terminology,
                                source_lang=source_lang, target_lang=target_lang)

        if combine_name:
            sections.append(result)

    if combine_name and sections:
        combined = "\n\n---\n\n".join(sections)
        out = output_dir / combine_name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(combined, encoding="utf-8")
        click.echo(f"\nCombined document saved: {out} ({len(combined.split())} words)")

    click.echo("\nDone.")


if __name__ == "__main__":
    translate()
