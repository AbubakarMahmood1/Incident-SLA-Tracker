#!/usr/bin/env python3
"""Verify repository-local documentation contracts."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
REQUIREMENT_PATTERN = re.compile(r"\b(?:FR|NFR)-\d{3}\b")
RECORD_PATTERN = re.compile(r"^\d{4}-.+\.md$")


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)


def prose_without_fences(text: str) -> str:
    lines: list[str] = []
    inside_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            inside_fence = not inside_fence
            continue
        if not inside_fence:
            lines.append(line)
    return "\n".join(lines)


def heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    occurrences: Counter[str] = Counter()
    for heading in HEADING_PATTERN.findall(text):
        plain = re.sub(r"<[^>]+>", "", heading)
        plain = re.sub(r"[`*_~]", "", plain).strip().lower()
        base = re.sub(r"[^\w\- ]", "", plain).replace(" ", "-")
        suffix = occurrences[base]
        occurrences[base] += 1
        anchors.add(base if suffix == 0 else f"{base}-{suffix}")
    return anchors


def normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1]
    return target.split(maxsplit=1)[0]


def verify_links(files: list[Path]) -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for source in files:
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(prose_without_fences(text)):
            target = normalize_link_target(raw_target)
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("//"):
                continue
            relative_path = unquote(parsed.path)
            destination = source if not relative_path else (source.parent / relative_path).resolve()
            try:
                destination.relative_to(ROOT)
            except ValueError:
                errors.append(f"{source.relative_to(ROOT)}: link escapes repository: {target}")
                continue
            if not destination.exists():
                errors.append(f"{source.relative_to(ROOT)}: missing link target: {target}")
                continue
            if parsed.fragment and destination.is_file() and destination.suffix.lower() == ".md":
                anchors = anchor_cache.setdefault(
                    destination,
                    heading_anchors(destination.read_text(encoding="utf-8")),
                )
                fragment = unquote(parsed.fragment).lower()
                if fragment not in anchors:
                    errors.append(
                        f"{source.relative_to(ROOT)}: missing anchor #{parsed.fragment} "
                        f"in {destination.relative_to(ROOT)}"
                    )
    return errors


def verify_requirement_traceability() -> list[str]:
    errors: list[str] = []
    srs_ids = REQUIREMENT_PATTERN.findall((ROOT / "docs/SRS.md").read_text(encoding="utf-8"))
    trace_ids = REQUIREMENT_PATTERN.findall(
        (ROOT / "docs/TRACEABILITY.md").read_text(encoding="utf-8")
    )
    for label, identifiers in (("SRS", srs_ids), ("traceability", trace_ids)):
        duplicates = sorted(
            identifier for identifier, count in Counter(identifiers).items() if count != 1
        )
        if duplicates:
            errors.append(f"{label} requirement IDs must occur once: {', '.join(duplicates)}")
    missing_from_trace = sorted(set(srs_ids) - set(trace_ids))
    missing_from_srs = sorted(set(trace_ids) - set(srs_ids))
    if missing_from_trace:
        errors.append(f"requirements missing from traceability: {', '.join(missing_from_trace)}")
    if missing_from_srs:
        errors.append(f"traceability IDs missing from SRS: {', '.join(missing_from_srs)}")
    return errors


def verify_record_indexes() -> list[str]:
    errors: list[str] = []
    for directory in (ROOT / "docs/adr", ROOT / "docs/rfc"):
        index = (directory / "README.md").read_text(encoding="utf-8")
        records = sorted(
            path.name for path in directory.glob("*.md") if RECORD_PATTERN.fullmatch(path.name)
        )
        for record in records:
            if index.count(record) != 1:
                errors.append(
                    f"{directory.relative_to(ROOT)}/README.md must link {record} exactly once"
                )
    return errors


def verify_mermaid_fences(files: list[Path]) -> list[str]:
    errors: list[str] = []
    diagram_count = 0
    for source in files:
        text = source.read_text(encoding="utf-8")
        openings = len(re.findall(r"^```mermaid\s*$", text, flags=re.MULTILINE))
        blocks = re.findall(r"^```mermaid\s*\n(.*?)^```\s*$", text, flags=re.MULTILINE | re.DOTALL)
        if openings != len(blocks):
            errors.append(f"{source.relative_to(ROOT)}: unclosed Mermaid fence")
        for block in blocks:
            diagram_count += 1
            if not block.strip():
                errors.append(f"{source.relative_to(ROOT)}: empty Mermaid block")
    if diagram_count == 0:
        errors.append("no Mermaid diagrams found")
    return errors


def main() -> int:
    files = markdown_files()
    errors = [
        *verify_links(files),
        *verify_requirement_traceability(),
        *verify_record_indexes(),
        *verify_mermaid_fences(files),
    ]
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"documentation contracts verified across {len(files)} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
