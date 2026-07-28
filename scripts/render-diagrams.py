#!/usr/bin/env python3
"""Extract and optionally render every repository Mermaid diagram."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERMAID_CLI = "@mermaid-js/mermaid-cli@11.16.0"


def diagrams() -> list[tuple[str, str]]:
    extracted: list[tuple[str, str]] = []
    files = sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)
    for source in files:
        text = source.read_text(encoding="utf-8")
        blocks = re.findall(r"^```mermaid\s*\n(.*?)^```\s*$", text, flags=re.MULTILINE | re.DOTALL)
        stem = re.sub(r"[^A-Za-z0-9]+", "-", str(source.relative_to(ROOT))).strip("-")
        extracted.extend(
            (f"{stem}-{index:02d}", block.strip() + "\n")
            for index, block in enumerate(blocks, start=1)
        )
    return extracted


def render(source: Path, destination: Path) -> None:
    if os.name == "nt":
        command = ["cmd", "/c", "npx", "--yes", MERMAID_CLI]
    else:
        command = ["npx", "--yes", MERMAID_CLI]
    subprocess.run(
        [*command, "--input", str(source), "--output", str(destination)],
        check=True,
        cwd=ROOT,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    extracted = diagrams()
    if not extracted:
        raise SystemExit("no Mermaid diagrams found")
    if args.render and args.output is None:
        parser.error("--render requires --output")
    if args.output is not None:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        for name, content in extracted:
            source = output / f"{name}.mmd"
            source.write_text(content, encoding="utf-8")
            if args.render:
                render(source, output / f"{name}.svg")
    print(f"{len(extracted)} Mermaid diagrams parsed" + (" and rendered" if args.render else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
