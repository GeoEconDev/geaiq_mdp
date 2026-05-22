"""
Migrates metadata YAML files from the old source format to the new nested format.

Old format:
    source_type: query
    source: |
      SELECT * FROM `project.dataset.table`

    source_type: shape
    source:
      - https://drive.google.com/file/d/...

New format:
    source:
      type: sql
      platform: bigquery
      query: |
        SELECT * FROM `project.dataset.table`

    source:
      type: shape
      platform: googledrive
      files:
        - https://drive.google.com/file/d/...

The script operates on raw text (not parsed YAML) so cross-file anchor
aliases like *GroupArg, *Per2023, etc. are never touched and remain intact.

Usage:
    # Preview changes without writing:
    python scripts/migrate_source_yaml.py --dry-run

    # Migrate all metadata files:
    python scripts/migrate_source_yaml.py

    # Migrate a single country directory:
    python scripts/migrate_source_yaml.py --path metadata/argentina

    # Migrate a single file:
    python scripts/migrate_source_yaml.py --path metadata/argentina/arg2023-prestamos-adm01.yml
"""
import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent

TYPE_MAP = {
    "query": ("sql", "bigquery"),
    "TODO":  ("sql", "bigquery"),
    "shape": ("shape", "googledrive"),
}


def reindent_block(lines: list[str], extra: str) -> list[str]:
    """Add `extra` spaces to the start of non-blank lines (preserves blank lines)."""
    result = []
    for line in lines:
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped.strip():
            result.append(extra + line)
        else:
            result.append(line)
    return result


def migrate_content(text: str) -> tuple[str, int]:
    """
    Rewrites source_type + source blocks in-place using line-by-line text processing.
    Anchor aliases (*GroupArg, *Per2023, etc.) in other fields are never touched.
    Returns (new_text, number_of_sources_changed).
    """
    lines = text.splitlines(keepends=True)
    result = []
    changes = 0
    i = 0

    while i < len(lines):
        raw = lines[i]
        stripped = raw.rstrip("\n").rstrip("\r")

        # Detect: <indent>source_type: (query|TODO|shape)
        m = re.match(r"^(\s*)source_type:\s*(query|TODO|shape)\s*$", stripped)
        if not m:
            result.append(raw)
            i += 1
            continue

        indent = m.group(1)
        indent_len = len(indent)
        src_type = m.group(2)
        i += 1  # consume source_type line

        # Collect blank/comment lines between source_type and source:
        between: list[str] = []
        found_source = False
        while i < len(lines):
            bl = lines[i].rstrip("\n").rstrip("\r")
            if bl.strip() == "" or bl.lstrip().startswith("#"):
                between.append(lines[i])
                i += 1
                continue
            if re.match(r"^" + re.escape(indent) + r"source\s*:", bl):
                found_source = True
                break
            # Hit a different key at same/lesser indent — give up
            break

        if not found_source:
            # Restore source_type and collected lines as-is
            result.append(raw)
            result.extend(between)
            continue

        source_line = lines[i].rstrip("\n").rstrip("\r")
        i += 1  # consume source: line

        # What follows source: on the same line?
        m2 = re.match(r"^" + re.escape(indent) + r"source\s*:\s*(.*)$", source_line)
        rest = m2.group(1).strip() if m2 else ""

        new_type, new_platform = TYPE_MAP[src_type]

        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            # Literal / folded block — collect indented content lines
            block_indicator = rest
            block_lines: list[str] = []
            while i < len(lines):
                bl = lines[i].rstrip("\n").rstrip("\r")
                if bl.strip() == "" or len(bl) - len(bl.lstrip()) > indent_len:
                    block_lines.append(lines[i])
                    i += 1
                else:
                    break

            result.extend(between)
            result.append(f"{indent}source:\n")
            result.append(f"{indent}  type: {new_type}\n")
            result.append(f"{indent}  platform: {new_platform}\n")
            if new_type == "sql":
                result.append(f"{indent}  query: {block_indicator}\n")
            else:
                result.append(f"{indent}  files: {block_indicator}\n")
            result.extend(reindent_block(block_lines, "  "))
            changes += 1

        elif rest == "":
            # source: (nothing inline) — collect deeper-indented block (list items, etc.)
            block_lines = []
            while i < len(lines):
                bl = lines[i].rstrip("\n").rstrip("\r")
                if bl.strip() == "" or len(bl) - len(bl.lstrip()) > indent_len:
                    block_lines.append(lines[i])
                    i += 1
                else:
                    break

            result.extend(between)
            result.append(f"{indent}source:\n")
            result.append(f"{indent}  type: {new_type}\n")
            result.append(f"{indent}  platform: {new_platform}\n")
            if new_type == "sql":
                result.append(f"{indent}  query:\n")
            else:
                result.append(f"{indent}  files:\n")
            result.extend(reindent_block(block_lines, "  "))
            changes += 1

        else:
            # source: inline_scalar
            result.extend(between)
            result.append(f"{indent}source:\n")
            result.append(f"{indent}  type: {new_type}\n")
            result.append(f"{indent}  platform: {new_platform}\n")
            if new_type == "sql":
                result.append(f"{indent}  query: {rest}\n")
            else:
                result.append(f"{indent}  files:\n")
                result.append(f"{indent}    - {rest}\n")
            changes += 1

    return "".join(result), changes


def migrate_file(path: Path, dry_run: bool) -> int:
    original = path.read_text(encoding="utf-8")
    new_text, count = migrate_content(original)
    if count and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return count


def collect_yaml_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.yml")) + sorted(root.rglob("*.yaml"))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        default="metadata",
        help="File or directory to migrate (default: metadata/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    args = parser.parse_args()

    target = REPO_ROOT / args.path
    if not target.exists():
        print(f"ERROR: path not found: {target}")
        sys.exit(1)

    files = collect_yaml_files(target)
    if not files:
        print("No YAML files found.")
        sys.exit(0)

    mode_label = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode_label}Scanning {len(files)} file(s) under {target}\n")

    files_changed = 0
    sources_changed = 0

    for path in files:
        count = migrate_file(path, args.dry_run)
        if count:
            files_changed += 1
            sources_changed += count
            rel = path.relative_to(REPO_ROOT)
            verb = "would update" if args.dry_run else "updated"
            print(f"  {verb}: {rel}  ({count} source{'s' if count > 1 else ''})")

    print(
        f"\nDone. {files_changed} file(s), {sources_changed} source(s) "
        f"{'would be ' if args.dry_run else ''}migrated."
    )
    if args.dry_run and sources_changed:
        print("Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
