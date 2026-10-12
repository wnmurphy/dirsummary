# dirsummary

Summarise a directory's contents: for each **file type** (by extension) it
reports the file count and total size, and a grand total across the whole tree.

Standard library only. No dependencies. Python 3.7+.

## Usage

```bash
# human-readable table (default)
python -m dirsummary some/path

# machine-readable JSON
python -m dirsummary some/path --json
```

The path defaults to the current directory (`.`) when omitted.

If you install it (`pip install .`), a `dirsummary` console script is also
available, but `python -m dirsummary` works with no install step.

## Example

For a tree holding two small `.py` files, a 5 KB `logo.png`, and a 200-byte
`data.bin`:

```
$ python -m dirsummary demo
   1  .png                 4.9 KB
   1  .bin                  200 B
   2  .py                    11 B
----------------------------------
4 files, 5.1 KB total

$ python -m dirsummary demo --json
{"path": "/…/demo", "total_files": 4, "total_bytes": 5211,
 "by_type": [{"type": ".png", "count": 1, "total_bytes": 5000},
             {"type": ".bin", "count": 1, "total_bytes": 200},
             {"type": ".py", "count": 2, "total_bytes": 11}]}
```

## Behavior notes

- **By extension.** Types are grouped case-insensitively; the same canonical
  key (dotted, lowercased, e.g. `.py`) appears in both the human and JSON
  output. A file with no extension is bucketed as `(no extension)`.
- **Human-size step** is binary (÷1024), one decimal from KB up (`1500 B` →
  `1.5 KB`); a JSON payload carries raw byte integers, never the formatted
  strings.
- **Symlinks** are counted as their own `(symlink)` bucket and are *never
  followed* — a symlink to a directory is counted once, not descended into
  (no infinite loops).
- **Broken or unreadable entries** are skipped, not fatal. An unreadable
  sub-tree adds an error line to stderr but the run still finishes (exit 0).
- **Hidden files** are included. Directories themselves are *traversed but not
  counted* as files.
- **Sorting.** The per-type rows are ordered by total size, largest first;
  ties broken alphabetically by type name, so output is deterministic.
- **Exit codes.** `0` on success. `1` if the argument is not a directory or
  does not exist (the error message goes to stderr, stdout stays empty, so a
  bad invocation never pollutes a pipeline).

## Layout

```
dirsummary/
  dirsummary/
    summary.py   # pure, side-effect-free logic: classify, collect,
                 # summarize, human_lines/human_table, render_json
    cli.py       # argparse, path validation, output dispatch, main(argv)
    __main__.py  # enables `python -m dirsummary`
  tests/
    test_summary.py
    test_cli.py
  docs/
    design.md
    plans/
```

Run the tests with `python -m pytest` from this directory.
