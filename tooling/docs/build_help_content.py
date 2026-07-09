#!/usr/bin/env python3
"""Render the shared help snippets to a keyed JSON the frontend loads at runtime.

Each `docs/user/_help/<key>.md` snippet becomes `{ "<key>": "<html>" }` in
help-content.json. The very same snippet files are pulled into the full docs
pages via pymdownx.snippets (`--8<-- "_help/<key>.md"`), so a help blurb is
authored once, in the docs tree, and shown both in the docs and in the in-app
help popover.

Run after `mkdocs build`; defaults write into the built site so nginx serves
the JSON next to the docs at /docs/help-content.json.

    python tooling/docs/build_help_content.py [SRC_DIR] [OUT_FILE]
"""

import json
import sys
from pathlib import Path

import markdown


def build(src: Path, out: Path) -> dict[str, str]:
    md = markdown.Markdown(extensions=["extra", "sane_lists"])
    content: dict[str, str] = {}
    for path in sorted(src.glob("*.md")):
        md.reset()
        content[path.stem] = md.convert(path.read_text(encoding="utf-8")).strip()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(content, indent=2, sort_keys=True), encoding="utf-8")
    return content


if __name__ == "__main__":
    src_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/user/_help")
    out_file = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("site/help-content.json")
    )
    result = build(src_dir, out_file)
    print(f"wrote {out_file} ({len(result)} snippet(s): {', '.join(result) or 'none'})")
