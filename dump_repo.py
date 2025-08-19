#!/usr/bin/env python3
"""
Dump selected source files from a repo into one or more text files, with clear file headers.

- Includes: .py, .html, .htm, .css, .js  (optionally .ts/.tsx via --include-ts)
- Skips: virtualenvs, .git, node_modules, caches, build artifacts, etc.
- Avoids minified assets (*.min.js, *.min.css) by default.
- Handles weird encodings gracefully.
- Can split output into multiple chunks by size.

Usage:
  python dump_repo.py --root . --out repo_dump.txt
  python dump_repo.py --root /path/to/repo --out dump.txt --max-chunk-mb 20 --include-ts
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

DEFAULT_EXTS = {".py", ".pyw", ".html", ".htm", ".css", ".js"}
TS_EXTS = {".ts", ".tsx"}
# Directories to always skip (case-sensitive directory names)
SKIP_DIRS = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".cache",
    "node_modules", "bower_components",
    "dist", "build", ".next", "out", "coverage", "site-packages", ".tox",
    ".idea", ".vscode"
}
# File name patterns (suffix-based) to skip
SKIP_SUFFIXES = {
    ".min.js", ".min.css",
}
# Extra large single-file cap (bytes). 0 = no per-file cap.
DEFAULT_PER_FILE_MAX = 0

HEADER_LINE = "=" * 80

def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIRS

def should_include_file(path: Path, allowed_exts: set[str], skip_suffixes: set[str]) -> bool:
    name = path.name
    # Skip obvious binary or minified variants by suffix
    for suf in skip_suffixes:
        if name.endswith(suf):
            return False
    return path.suffix.lower() in allowed_exts

def write_section(writer, rel_path: str, text: str):
    writer.write(f"{HEADER_LINE}\n")
    writer.write(f"BEGIN FILE: {rel_path}\n")
    writer.write(f"{HEADER_LINE}\n")
    writer.write(text)
    if text and not text.endswith("\n"):
        writer.write("\n")
    writer.write(f"{HEADER_LINE}\n")
    writer.write(f"END FILE: {rel_path}\n")
    writer.write(f"{HEADER_LINE}\n\n")

def iter_files(root: Path, allowed_exts: set[str], skip_suffixes: set[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        # prune directories in-place
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for fname in filenames:
            p = Path(dirpath) / fname
            if should_include_file(p, allowed_exts, skip_suffixes):
                yield p

def read_text_best_effort(p: Path, per_file_max: int) -> str:
    # Try UTF-8 first, then fall back to latin-1 as a last resort, replacing errors.
    size = p.stat().st_size
    if per_file_max > 0 and size > per_file_max:
        # Read only the head/tail around per_file_max bytes, with a notice
        head_bytes = per_file_max // 2
        tail_bytes = per_file_max - head_bytes
        try:
            with p.open("rb") as f:
                head = f.read(head_bytes)
                if size > head_bytes:
                    f.seek(max(0, size - tail_bytes))
                    tail = f.read(tail_bytes)
                else:
                    tail = b""
            head_txt = head.decode("utf-8", errors="replace")
            tail_txt = tail.decode("utf-8", errors="replace")
        except Exception:
            # last resort
            head_txt = head.decode("latin-1", errors="replace")
            tail_txt = tail.decode("latin-1", errors="replace")

        notice = (
            f"\n\n<<< NOTE: file truncated for size ({size} bytes); "
            f"showing first {head_bytes} bytes and last {tail_bytes} bytes >>>\n\n"
        )
        return head_txt + notice + tail_txt

    # Normal full read
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return p.read_text(encoding="latin-1", errors="replace")

def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def next_chunk_path(base: Path, idx: int) -> Path:
    if idx == 1:
        return base
    stem = base.stem
    return base.with_name(f"{stem}.part{idx}{base.suffix}")

def dump_repo(
    root: Path,
    out_path: Path,
    allowed_exts: set[str],
    skip_suffixes: set[str],
    per_file_max: int,
    max_chunk_mb: int,
):
    files = sorted(iter_files(root, allowed_exts, skip_suffixes))
    if not files:
        print("No matching files found.", file=sys.stderr)
        return

    max_chunk_bytes = max_chunk_mb * 1024 * 1024 if max_chunk_mb > 0 else 0
    chunk_idx = 1
    current_out = next_chunk_path(out_path, chunk_idx)
    ensure_parent(current_out)
    writer = current_out.open("w", encoding="utf-8", newline="\n")
    written_bytes = 0

    def rotate_writer():
        nonlocal writer, written_bytes, chunk_idx, current_out
        if writer:
            writer.close()
        chunk_idx += 1
        current_out = next_chunk_path(out_path, chunk_idx)
        ensure_parent(current_out)
        writer = current_out.open("w", encoding="utf-8", newline="\n")
        written_bytes = 0

    root = root.resolve()
    for p in files:
        rel_path = str(p.resolve().relative_to(root))
        text = read_text_best_effort(p, per_file_max)
        section = []
        section.append(f"{HEADER_LINE}\n")
        section.append(f"BEGIN FILE: {rel_path}\n")
        section.append(f"{HEADER_LINE}\n")
        section.append(text)
        if text and not text.endswith("\n"):
            section.append("\n")
        section.append(f"{HEADER_LINE}\n")
        section.append(f"END FILE: {rel_path}\n")
        section.append(f"{HEADER_LINE}\n\n")
        blob = "".join(section)
        blob_bytes = len(blob.encode("utf-8", errors="replace"))

        if max_chunk_bytes and written_bytes + blob_bytes > max_chunk_bytes and written_bytes > 0:
            rotate_writer()

        writer.write(blob)
        written_bytes += blob_bytes

    writer.close()
    print(f"Done. Wrote {chunk_idx} file(s) starting at: {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Dump repo source files into a text bundle.")
    ap.add_argument("--root", default=".", help="Repo root directory (default: .)")
    ap.add_argument("--out", default="repo_dump.txt", help="Output file path (default: repo_dump.txt)")
    ap.add_argument("--include-ts", action="store_true", help="Also include .ts/.tsx files")
    ap.add_argument("--include-min", action="store_true", help="Include *.min.js and *.min.css")
    ap.add_argument("--per-file-max-bytes", type=int, default=DEFAULT_PER_FILE_MAX,
                    help="Maximum bytes to read per file (0 = no limit).")
    ap.add_argument("--max-chunk-mb", type=int, default=0,
                    help="Split output into ~N MB chunks (0 = single file).")
    args = ap.parse_args()

    allowed = set(DEFAULT_EXTS)
    if args.include_ts:
        allowed |= TS_EXTS

    skip_suffixes = set() if args.include_min else set(SKIP_SUFFIXES)

    dump_repo(
        root=Path(args.root),
        out_path=Path(args.out),
        allowed_exts=allowed,
        skip_suffixes=skip_suffixes,
        per_file_max=args.per_file_max_bytes,
        max_chunk_mb=args.max_chunk_mb,
    )

if __name__ == "__main__":
    main()
