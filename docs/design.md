# dirsummary — Design

A simple, dependency-free Python 3 CLI that takes a directory path and
prints a summary of the files it contains, grouped by file type (extension),
with per-type and total sizes.

**Date:** 2026-10-11
**Status:** approved by user (default choices taken from the brainstorming prompt)

## Intent & why

You want a fast, one-shot answer to "what's actually in this tree, and how
big are the categories?" — e.g. "is this directory mostly images, source, or
log files, and roughly how full is it?" It must be runnable anywhere Python 3
is present, with no install step, and it must not crash on the messy things
real directories contain (broken symlinks, unreadable files, odd dotfiles).

## Goals

- Take a directory path and report, per type: file count and total byte size.
- Classify by **file extension**, grouped case-insensitively.
- Recurse the tree; include hidden files; **don't** follow symlinks (count them
  as their own bucket); skip broken/unreadable entries instead of crashing.
- Two output modes: a human-readable grouped table by default, and a
  machine-readable JSON via `--json`.
- Pure logic separated from I/O so it is unit-testable with no filesystem in
  the way and no side effects.

## Non-goals / anti-goals

- **No dependencies.** Stdlib only. No `python-magic`, no `click`.
- **Not a file-contents analysis.** Type = extension only. No MIME sniffing,
  no hashing, no duplicate detection.
- **Not a general-purpose scanner.** No globbing, no filtering by
  `.gitignore`, no progress bars, no color (keep it pipeable and quiet).
- **No persistence / no config files.** Stateless.
- A failure that "works technically but lies" (e.g. silently double-counting
  symlinks, or crashing on one bad file and dropping the whole run) is a
  worse outcome than a correct, quiet run.

## Constraints

- Python **3.7+**, standard library only. No syntax newer than 3.7 (no walrus,
  no `str.removeprefix`).
- Must run from a clean checkout with no install/deps.
- Tests are hermetic: they build a real fixture tree under a temp dir and
  never touch the real home directory.
- Must not follow symlink loops (`os.walk(..., followlinks=False)`).

## Decided "how" (from the brainstorming prompt + my calls)

| Area | Decision | Decided by |
|------|----------|------------|
| Location | new top-level `dirsummary/` dir at repo root | user |
| File type | by extension | user |
| Output | human-readable by default, `--json` flag for JSON | user |
| Scanning | recurse; include hidden; count symlinks without following; skip broken/unreadable gracefully | user |
| CLI framework | stdlib `argparse` | my call (keeps us dep-free) |
| Layout | `dirsummary/summary.py` (pure logic) + `dirsummary/cli.py` (`main(argv)`, I/O) + `tests/` | my call (clean I/pure split for TDD) |
| Extension grouping | canonical key = extension **with** leading dot, lowercased (`.py`; `.PNG`→`.py`); no extension → `(no extension)`; same key used in human and JSON | my call |
| Symlinks | counted as a `(symlink)` bucket; target not read, not followed; broken links also `(symlink)` | my call |
| Directory entries | directories are traversed but **not** counted as "files" | my call |
| Size source | regular files: `lstat().st_size`; symlinks: `lstat().st_size` (link size, not target) | my call |
| Human row sort | by total bytes **desc**, ties broken by type name asc | my call |
| Human size format | `B / KB / MB / GB / TB` in binary steps (÷1024), one decimal, e.g. `1.5 KB` | my call |
| JSON payload | object: `{path, total_files, total_bytes, by_type:[{type,count,total_bytes}]}`; **raw ints**, no human strings | my call |
| Default path arg | `.` (current dir) when the positional is omitted | my call |
| Bad input | path missing or is a file (not a dir): message to **stderr**, exit code **1** | my call |
| Mid-walk error | an unreadable/broken entry is skipped; an optional note goes to **stderr**; run still succeeds (exit 0) | my call |
| Empty dir | 0 files, empty `by_type`, `0 B` total — still prints cleanly | my call |
| Tests | pytest, hermetic fixture tree via `tmp_path` | my call (pytest 5.4 present) |

## Output shape

Human-readable (default):

```
 24  .py             12.3 KB
  8  .md             4.1 KB
  3  (symlink)         80 B
  5  (no extension)  1.0 KB
--------------------------
40 files, 17.5 KB total
```

JSON (`--json`):

```json
{
  "path": "/abs/path",
  "total_files": 40,
  "total_bytes": 18096,
  "by_type": [
    {"type": ".py", "count": 24, "total_bytes": 12576},
    {"type": ".md", "count": 8,  "total_bytes": 4194}
  ]
}
```

Notes: both the human table and the JSON payload use the same canonical type
key (extension with a leading dot, lowercased; or the reserved words
`(no extension)` / `(symlink)`). JSON carries raw byte integers, never the
human-formatted strings.

## What's left for the builder

- Exact whitespace/alignment of the human table and the precise human-size
  rounding (plan pins these down so tests can assert exact strings).
- The `path` field in JSON: absolute real path. Confirm in plan.
- Final CLI entry point: `python -m dirsummary` and/or `python -m dirsummary.cli`.

## Builder check

Reviewed as a builder (self-review; project is simple enough that a full
subagent check is disproportionate). No unresolved "must the user answer
this" questions remain — every open point has a sensible default marked in
the "how" table above. The only genuinely user-visible defaults are captured
there for their review.
