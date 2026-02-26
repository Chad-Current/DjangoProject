#!/usr/bin/env python3
"""
fix_template_urls.py
--------------------
Run from your Django project root:

    python fix_template_urls.py --dry-run   # preview only
    python fix_template_urls.py             # apply changes

Fixes positional pk arguments in {% url %} tags, e.g.:

    BEFORE:  {% url 'dashboard:account_detail' account.pk %}
    AFTER:   {% url 'dashboard:account_detail' account.slug %}

A .bak backup is written next to each changed file before it is modified.
"""

import re
import sys
from pathlib import Path

DRY_RUN   = "--dry-run" in sys.argv
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "migrations"}

SLUG_VIEWS = [
    "account_detail",   "account_update",   "account_delete",
    "contact_detail",   "contact_update",   "contact_delete",
    "device_detail",    "device_update",    "device_delete",
    "estate_detail",    "estate_update",    "estate_delete",
    "importantdocument_detail", "importantdocument_update", "importantdocument_delete",
    "familyawareness_detail",   "familyawareness_update",   "familyawareness_delete",
    "relevancereview_detail",   "relevancereview_update",   "relevancereview_delete",
    "mark_item_reviewed",
]


def fix_line(line):
    changes = []

    if "url" not in line or ".pk" not in line:
        return line, changes

    for view_name in SLUG_VIEWS:
        pattern = re.compile(
            r"("
            r"\{%-?\s*url\s+"
            r"['\"][^'\"]*" + re.escape(view_name) + r"[^'\"]*['\"]"
            r"[^%]*?"
            r"\w+"
            r")\.pk"
            r"([^%]*%-?\})"
        )
        new_line = pattern.sub(r"\1.slug\2", line)
        if new_line != line:
            changes.append(view_name)
            line = new_line

    return line, changes


def process_file(path):
    original  = path.read_text(encoding="utf-8")
    lines     = original.splitlines(keepends=True)
    new_lines = []
    changed   = 0

    for i, line in enumerate(lines, 1):
        new_line, notes = fix_line(line)
        new_lines.append(new_line)
        if notes:
            changed += 1
            print(f"    line {i:4d}: {', '.join(notes)}")
            print(f"             WAS: {line.rstrip()}")
            print(f"             NOW: {new_line.rstrip()}")

    if changed and not DRY_RUN:
        path.with_suffix(path.suffix + ".bak").write_text(original, encoding="utf-8")
        path.write_text("".join(new_lines), encoding="utf-8")
        print(f"  ✓ saved")

    return changed


def main():
    root  = Path(".")
    files = sorted(root.rglob("*.html"))

    if not files:
        print("No .html files found.")
        return

    total_files = total_lines = 0

    for f in files:
        if any(s in f.parts for s in SKIP_DIRS):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if "url" not in text or ".pk" not in text:
            continue

        print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}► {f}")
        n = process_file(f)
        if n:
            total_files += 1
            total_lines += n

    print(f"\n{'='*60}")
    print("DRY RUN — nothing written." if DRY_RUN else "Done.")
    print(f"  Files modified : {total_files}")
    print(f"  Lines changed  : {total_lines}")


if __name__ == "__main__":
    main()