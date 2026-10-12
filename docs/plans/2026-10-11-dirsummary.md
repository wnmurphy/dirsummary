# dirsummary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free Python 3 CLI that takes a directory path and
prints a summary of the files it contains — per type (extension): count and
total size — with a human-readable table by default and `--json` for machines.

**Architecture:** Pure, side-effect-free logic lives in `dirsummary/summary.py`
and is unit-tested in isolation; a thin I/O layer in `dirsummary/cli.py`
(`main(argv)`) parses args, validates the path, and renders a chosen output.
Tests build a real fixture tree under pytest's `tmp_path` and never touch the
developer's home directory.

**Tech Stack:** Python 3.7+ **stdlib only** (`os`, `argparse`, `json`,
`pathlib`, `dataclasses`); pytest for tests; no third-party packages.

**Spec:** `dirsummary/docs/design.md` (read it first — the plan argues from it).

## Global Constraints

These apply to every task; they need not be repeated in each one.

- Python **3.7+**, **standard library only**; no third-party dependencies.
- No syntax newer than 3.7: **no** walrus `:=`, **no** `str.removeprefix`/
  `removesuffix` (3.9+), **no** `match` (3.10+).
- Pure logic is importable and side-effect-free; only `cli.py` touches the
  filesystem/argparse/stdout.
- Symlinks are **counted, never followed** (`os.walk(..., followlinks=False)`).
- Broken/unreadable entries are **skipped, not fatal**.
- Canonical type key (used identically in human and JSON output): the extension
  **with a leading dot, lowercased** (``.PNG`` → ``.py``); no extension →
  `(no extension)`; any symlink → `(symlink)`.
- All tests are hermetic (use `tmp_path`); no test reads the developer's `$HOME`.
- One commit per task, after its tests pass.

## Review Focus

Failure modes the spec implies but a naive task list might not pin down. Each is
exercised by a test added to the owning task.

1. **Broken symlink / unreadable target** — must be skipped without aborting the
   run and without a traceback. → `collect` test (Task 3).
2. **Symlink-to-directory** — counted once as `(symlink)`, **and its children
   are NOT scanned** (no loop, no descent). → `collect` test (Task 3).
3. **Dotfiles / extension detection** — `.gitignore` and `Makefile` are
   `(no extension)`; `archive.tar.gz` is `.gz` (last extension). → `classify`
   test (Task 2).
4. **Sorting stability on equal totals** — two types with identical
   `total_bytes` must order deterministically (name ascending). → `summarize`
   test (Task 4).
5. **Empty directory** — `0 files, 0 B total` (human) and a well-formed JSON
   object with empty `by_type` (JSON). Both render cleanly, no crash. →
   `human_lines` test (Task 5) + `render_json` test (Task 6).

---

### Task 1: Scaffold the package and implement `format_size`

**Files:**
- Create: `dirsummary/__init__.py` (empty package marker)
- Create: `conftest.py` (empty — puts the project root on `sys.path` so
  `import dirsummary` works under pytest 5.x, which predates the `pythonpath`
  ini option)
- Create: `dirsummary/summary.py` (holds all pure functions; this task adds
  `format_size`)
- Test: `tests/test_summary.py`

**Interfaces:**
- Produces: `def format_size(n: int) -> str` — a non-negative integer count of
  bytes rendered as a human string, binary (÷1024) steps, one decimal for
  KB and up: `"0 B"`, `"1023 B"`, `"1.0 KB"`, `"12.3 KB"`, `"1.0 MB"`.
- No prior interfaces consumed.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_summary.py
from dirsummary.summary import format_size

def test_format_size_bytes():
    assert format_size(0) == "0 B"
    assert format_size(1) == "1 B"
    assert format_size(1023) == "1023 B"

def test_format_size_kb_mb_gb():
    assert format_size(1024) == "1.0 KB"
    assert format_size(12576) == "12.3 KB"        # 12334.0 -> 12.0? pin exact below
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.0 GB"
```

> **Pin the exact numbers before coding, don't guess.** `12.3 KB` above is a
> placeholder — work out the real rounded string for `12576` bytes
> (`12576 / 1024 == 12.3046875` → `.1f` → `"12.3 KB"`) and use whatever
> `"{:.1f}".format` actually produces. The test must reflect the real output,
> not a rounded-off intuition.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd dirsummary && python -m pytest tests/test_summary.py -v`
Expected: FAIL — `ImportError` / module or function not found.
(Also creates `__init__.py`, `conftest.py`, `tests/` per the Files list first,
so the import resolves and the failure is "function not found", not "cannot
import".)

- [ ] **Step 3: Implement `format_size` in `dirsummary/summary.py`**

Non-negative int. If `n < 1024`: `f"{n} B"`. Otherwise walk the units
`["KB","MB","GB","TB","PB","EB"]`, dividing the float value by 1024 each step
and returning `f"{value:.1f} {unit}"` at the first unit where `value < 1024`;
if it exhausts the list, return the last unit with the final value. (A body
appears only because the threshold/format loop is an algorithm the signature and
tests don't fully determine.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd dirsummary && python -m pytest tests/test_summary.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd dirsummary
git add __init__.py conftest.py summary_dir summary.py tests/test_summary.py  # use actual paths
git commit -m "feat: add format_size and scaffold dirsummary package"
```

> Use the real paths (`dirsummary/__init__.py`, `dirsummary/summary.py`, etc.);
> the placeholders above are illustrative. Initialize the git repo first with
> `git init` if none exists.

---

### Task 2: `classify` — type key from a name

**Files:**
- Modify: `dirsummary/summary.py` (add `classify`)
- Test: `tests/test_summary.py` (add tests)

**Interfaces:**
- Produces: `def classify(name: str, is_symlink: bool = False) -> str`
  → `(symlink)` when `is_symlink`; else the lowercased extension **with a
  leading dot** (``"a.PNG"`` → `".png"`); `(no extension)` when there is no
  extension after the first character.
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Write the failing tests**

```python
from dirsummary.summary import classify

def test_classify_extensions_case_insensitive():
    assert classify("a.py") == ".py"
    assert classify("a.PNG") == ".png"
    assert classify("archive.tar.gz") == ".gz"   # last extension wins

def test_classify_no_extension():
    assert classify("Makefile") == "(no extension)"
    assert classify(".gitignore") == "(no extension)"   # leading dot, no ext
    assert classify("a.") == "(no extension)"            # trailing dot

def test_classify_symlink():
    assert classify("anything", is_symlink=True) == "(symlink)"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_summary.py -k classify -v`
Expected: FAIL — `classify` not defined.

- [ ] **Step 3: Implement `classify` in `dirsummary/summary.py`**
`if is_symlink: return "(symlink)"`. Compute the extension as the substring
after the **last** dot; treat a leading dot in the basename as *not* an
extension (``".gitignore"`` → no extension). Empty remainder (`"a."`) →
`"(no extension)"`. Prefix the extension with `"."` and `.lower()` it. (Body
appears because the "last dot, ignoring a leading dot" rule is the tricky
part the signature hides.)

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_summary.py -k classify -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dirsummary/summary.py tests/test_summary.py
git commit -m "feat: classify files by extension (case-insensitive, dotfile-aware)"
```

---

### Task 3: `collect` — walk a tree robustly

**Files:**
- Modify: `dirsummary/summary.py` (add `collect` and a small entry type)
- Test: `tests/test_summary.py` (add tests, using `tmp_path`)

**Interfaces:**
- Produces: `def collect(path) -> list[tuple[str, int]]` — a list of
  `(type_key, size_bytes)` entries. Each entry is a regular file or a symlink;
  directories are not entries. Symlinks → `type_key == "(symlink)"` with the
  link's own `lstat().st_size`.
- Consumes: `classify(name, is_symlink)` (Task 2).
- Also produces (may be internal): a lightweight `Entry` — a 2-tuple
  `(type_key, size)` is fine; don't over-engineer a dataclass unless it earns
  its keep.

Robustness requirements (the Review Focus items):
- Recurse; include hidden files.
- Follow **no** symlinks. A symlink-to-dir appears in `os.walk`'s `dirnames`
  but is **not descended**; it is added as a single `(symlink)` entry.
- Broken symlinks and unreadable files are **skipped** (counted as nothing, or
  counted as `(symlink)` for the broken link *without* touching its target —
  pin this choice: **a broken symlink counts as `(symlink)` with size `0`**;
  an unreadable *regular* file is skipped entirely). Run never raises.

- [ ] **Step 1: Write the failing tests** (build trees with `tmp_path`)

```python
import os, stat

def _write(p, text=""):
    p.write_text(text)
    return p

def test_collect_basic(tmp_path):
    (tmp_path / "a.py").write_text("x"*100)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("y"*50)
    entries = dict_from_collect(collect(str(tmp_path)))
    assert entries[(".py")] == 100
    assert entries[(".txt")] == 50

def test_collect_hidden_included(tmp_path):
    (tmp_path / ".hidden").write_text("secret")
    types = {k for k, _ in collect(str(tmp_path))}
    assert ".hidden" in types

def test_collect_symlink_to_file(tmp_path):
    target = (tmp_path / "target.txt").write_text("hi")
    link = tmp_path / "link"
    os.symlink(str(target), str(link))
    entries = collect(str(tmp_path))
    # the link is its own (symlink) entry; target is .txt
    assert any(k == "(symlink)" for k, _ in entries)

def test_collect_symlink_to_dir_not_descended(tmp_path):
    real = (tmp_path / "real").mkdir()
    (real / "c.py").write_text("z")
    (tmp_path / "sublink").symlink_to(str(real))
    keys = [k for k, _ in collect(str(tmp_path))]
    # 'real' and its file appear once; sublink is counted once, NOT re-walked
    assert keys.count("(symlink)") == 1
    assert dict_from_collect(collect(str(tmp_path)))[".py"] == 1   # not 2

def test_collect_broken_symlink_no_crash(tmp_path):
    os.symlink(str(tmp_path / "does-not-exist"), str(tmp_path / "broken"))
    entries = collect(str(tmp_path))     # must not raise
    assert any(k == "(symlink)" for k, _ in entries)
```

> `dict_from_collect` is a tiny test helper (type_key → summed size) you may
> define once at the top of the test module; keep it out of production code.
> For the broken-symlink test, `lstat` on a broken link still succeeds (it
> stats the link, not the target), so size is the link's own size — confirm
> the exact number and assert it, or assert `>= 0`.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_summary.py -k collect -v`
Expected: FAIL — `collect` not defined.

- [ ] **Step 3: Implement `collect` in `dirsummary/summary.py`**

Walk with `os.walk(path, onerror=lambda e: None, followlinks=False)`. For each
directory level: for every name in `dirnames`, if `os.path.islink(full)` add
`(  classify(name, True), lstat_size)` (do **not** rely on descent — it's off);
for every name in `files`, if `os.path.islink(full)` add `(classify(name, True),
lstat_size)` else add `(classify(name, False), lstat_size)`. Wrap each
`lstat()` in `try/except OSError` and skip on failure. **Order the per-level
dirname/file handling so symlinked dirs are counted but never walked** — since
`followlinks=False`, children of a symlinked dir are never yielded; assert that
in the test. Body given because the "scan dirnames for links without descending"
behavior is the non-obvious part.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_summary.py -k collect -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dirsummary/summary.py tests/test_summary.py
git commit -m "feat: recursively collect entries, skipping broken/unreadable safely"
```

---

### Task 4: `summarize` — group, sort, total

**Files:**
- Modify: `dirsummary/summary.py` (add `summarize` and the result types)
- Test: `tests/test_summary.py`

**Interfaces:**
- Produces:
  - `def summarize(entries) -> Summary`
  - `Summary` (dataclass): `total_files: int`, `total_bytes: int`,
    `by_type: list[TypeStat]`.
  - `TypeStat` (dataclass): `type: str` (canonical key), `count: int`,
    `total_bytes: int`.
- `by_type` is sorted by `total_bytes` **descending**, ties broken by `type`
  **ascending**.
- Consumes: the `(type_key, size)` list from `collect` (Task 3); also works on
  a plain list passed directly, so it's unit-testable without a filesystem.

- [ ] **Step 1: Write the failing tests**

```python
from dirsummary.summary import summarize, TypeStat, Summary
from collections import namedtuple

def test_summarize_empty():
    s = summarize([])
    assert s.total_files == 0
    assert s.total_bytes == 0
    assert s.by_type == []

def test_summarize_groups_and_sorts_desc_by_bytes():
    entries = [(".py", 100), (".py", 50), (".txt", 300)]
    s = summarize(entries)
    assert s.total_files == 3
    assert s.total_bytes == 450
    assert [(t.type, t.count, t.total_bytes) for t in s.by_type] == [
        (".txt", 1, 300), (".py", 2, 150)
    ]

def test_summarize_tie_break_name_ascending():
    entries = [(".z", 10), (".a", 10)]
    s = summarize(entries)
    assert [t.type for t in s.by_type] == [".a", ".z"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_summary.py -k summarize -v`
Expected: FAIL — `summarize`/`Summary` undefined.

- [ ] **Step 3: Implement `summarize`, `Summary`, `TypeStat` in
`dirsummary/summary.py`**

Accumulate `{key: [count, total]}` over the entries, then build `TypeStat`
objects sorted by `(-total_bytes, type)`. `total_files == len(entries)`;
`total_bytes` is the sum. Use `@dataclass`. (Sort key is the one non-obvious
choice — pin it here so Task 5 and Task 6 reuse it.)

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_summary.py -k summarize -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dirsummary/summary.py tests/test_summary.py
git commit -m "feat: summarize entries into sorted per-type totals"
```

---

### Task 5: `human_lines` / `human_table` — human-readable rendering

**Files:**
- Modify: `dirsummary/summary.py` (add `human_lines`, and `human_table` as a
  thin join)
- Test: `tests/test_summary.py`

**Interfaces:**
- Produces: `def human_lines(summary: Summary, path_label: str) -> list[str]`
  and `def human_table(summary: Summary, path_label: str) -> str` (the two are
  split so the *lines* — the assertable unit with deterministic content — are
  tested directly, while `human_table` is just `"\n".join(human_lines(...))`).
  A row per `by_type` entry plus a trailing totals line
  (`"N files, X total"`); an empty summary yields only the totals line
  (`"0 files, 0 B total"`).
- Consumes: `Summary`/`TypeStat` (Task 4), `format_size` (Task 1).

- [ ] **Step 1: Write the failing tests**

```python
from dirsummary.summary import human_lines, human_table, summarize

def test_human_lines_rendering():
    s = summarize([(".md", 4194), (".py", 12576), (".py", 0)])
    lines = human_lines(s, "/home/x")
    lines = "\n".join(lines)
    assert "total" in lines.splitlines()[-1]
    assert lines.splitlines()[-1] == "3 files, 16.8 KB total"  # 4194+12576, pin it
    # largest-bytes first
    order = [ln for ln in lines if "files," not in ln]
    assert order[0].split()[1] == ".py"

def test_human_lines_empty():
    s = summarize([])
    lines = human_lines(s, "/x")
    assert lines == ["0 files, 0 B total"]

def test_human_table_is_join_of_lines():
    s = summarize([])
    assert human_table(s, "/x") == "\n".join(human_lines(s, "/x"))
```

> **Pin the totals numbers and the exact column format in the test, computing
> them by hand.** If the exact row alignment proves brittle, assert on the
> split-and-stripped row content (order + presence of each type key and size)
> rather than pixel-exact whitespace — the human table is decorative; the
> numbers and order are the contract. Record which approach you take in the
> commit.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_summary.py -k human -v`
Expected: FAIL — `human_lines` undefined.

- [ ] **Step 3: Implement `human_lines` and `human_table` in
`dirsummary/summary.py`**

One row per `TypeStat`: right-aligned count, fixed-width left-aligned `type`,
right-aligned `format_size(total_bytes)`. A trailing totals line
`f"{total_files} files, {format_size(total_bytes)} total"`. `human_table`
joins `human_lines` with `"\n"`. (Widths are a formatting choice — pin concrete
widths here so the test can match or the reviewer can see them.)

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_summary.py -k human -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dirsummary/summary.py tests/test_summary.py
git commit -m "feat: render a human-readable per-type table with totals"
```

---

### Task 6: `render_json` — machine-readable output

**Files:**
- Modify: `dirsummary/summary.py` (add `render_json`)
- Test: `tests/test_summary.py`

**Interfaces:**
- Produces: `def render_json(summary: Summary, path_label: str) -> str` — a
  compact JSON string (parse it back with `json.loads` in the test) for
  `{"path": path_label, "total_files": int, "total_bytes": int,
  "by_type": [{"type": str, "count": int, "total_bytes": int}, ...]}`.
  `by_type` keeps the same sort order as `Summary.by_type`; integers are raw
  bytes.
- Consumes: `Summary`/`TypeStat` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
import json
from dirsummary.summary import render_json, summarize

def test_render_json_structure_and_raw_bytes():
    s = summarize([(".py", 100), (".txt", 300)])
    doc = json.loads(render_json(s, "/home/x"))
    assert doc["path"] == "/home/x"
    assert doc["total_files"] == 2
    assert doc["total_bytes"] == 400
    assert doc["by_type"] == [
        {"type": ".txt", "count": 1, "total_bytes": 300},
        {"type": ".py", "count": 1, "total_bytes": 100},
    ]
    assert all(isinstance(t["total_bytes"], int) for t in doc["by_type"])

def test_render_json_empty():
    doc = json.loads(render_json(summarize([]), "/x"))
    assert doc == {"path": "/x", "total_files": 0,
                   "total_bytes": 0, "by_type": []}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_summary.py -k json -v`
Expected: FAIL — `render_json` undefined.

- [ ] **Step 3: Implement `render_json` in `dirsummary/summary.py`**

Build the plain dict (no dataclass serialization magic needed — assemble by
hand) and `json.dumps` it. Integers stay integers; no human strings leak in.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_summary.py -k json -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dirsummary/summary.py tests/test_summary.py
git commit -m "feat: JSON output via render_json"
```

---

### Task 7: `main` / `cli.py` — argparse, path validation, dispatch, exit codes

**Files:**
- Create: `dirsummary/cli.py` (`def main(argv=None) -> int`, plus a
  `if __name__ == "__main__": sys.exit(main())` guard)
- Create: `dirsummary/__main__.py` (so `python -m dirsummary` runs `main`)
- Test: `tests/test_cli.py` (new file)

**Interfaces:**
- Produces: `def main(argv: list[str] | None = None) -> int` — returns the
  process exit code. Exit `0` on success (prints the chosen output to stdout);
  exit `1` on bad input (message to **stderr**, nothing to stdout).
- CLI surface: positional `path` (`nargs="?"`, **default `"."`**) and a
  `--json` flag.
- Consumes: `collect`, `summarize`, `human_table`, `render_json` from Task 3–6;
  `path_label` for the output is `str(Path(path).resolve())`.

Path validation (exit 1, message to stderr, **nothing** to stdout):
- path does not exist.
- path exists but is **not** a directory (a regular file — including a symlink
  resolving to a file).

- [ ] **Step 1: Write the failing tests** (`tests/test_cli.py`, using
`tmp_path` + `capsys`)

```python
from dirsummary.cli import main

def test_main_human_output(tmp_path, capsys):
    (tmp_path / "a.py").write_text("x" * 1024)
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert ".py" in out

def test_main_json_output(tmp_path, capsys):
    (tmp_path / "a.py").write_text("x" * 1024)
    assert main([str(tmp_path), "--json"]) == 0
    out = capsys.readouterr().out
    assert '"total_files"' in out and '"by_type"' in out

def test_main_empty_dir(tmp_path, capsys):
    assert main([str(tmp_path)]) == 0
    assert "0 files" in capsys.readouterr().out

def test_main_missing_path_exits_1(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 1
    assert capsys.readouterr().out == ""       # stderr only
    assert capsys.readouterr().err != ""

def test_main_file_not_dir_exits_1(tmp_path, capsys):
    f = (tmp_path / "a.txt").write_text("hi")
    assert main([str(f)]) == 1
    assert capsys.readouterr().out == ""
```

> `capsys` captures only one read per `readouterr()`; the exact assertion on
> which buffer is empty must match real behavior — assert the buffer that *is*
> empty, and read a fresh `readouterr()` for the *other* buffer in the same
> test (you can't read both from one call). Adjust the test so each buffer get
> its own `readouterr()`.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `cli` module / `main` not defined.

- [ ] **Step 3: Implement `main` in `dirsummary/cli.py` and add
`dirsummary/__main__.py`**

`argparse` with `nargs="?"` default `.` and `--json` (store_true). Validate the
path: if `not os.path.exists(path)` or `not os.path.isdir(path)` → write a
message to `sys.stderr` and return `1` (and do **not** print to stdout).
Otherwise: `collect` → `summarize`, then print `render_json(...)` if
`args.json` else `human_table(...)`, using `path_label = str(Path(path).
resolve())`. Return `0`. `__main__.py` re-exports `main` and calls it with
`sys.exit(main())`. Body given for the argparse spec and the exact
`os.path.isdir` vs `islink` handling because that validation is the tricky
behavior the tests pin.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dirsummary/cli.py dirsummary/__main__.py tests/test_cli.py
git commit -m "feat: CLI entry point with argparse, path validation, --json"
```

---

### Task 8: Pack the project, document it, and smoke-test the real binary

**Files:**
- Create: `dirsummary/pyproject.toml` (minimal metadata + a
  `dirsummary = "dirsummary.cli:main"` console entry point, plus a
  `project.scripts` mapping that lets `pip install -e .` expose a
  `dirsummary` command — do **not** rely on install for tests)
- Create: `dirsummary/README.md` (usage, `--json`, examples, "no deps")
- Test: no new unit test; this task's deliverable is a **real invocation** of
  the installed module, which is itself the test (and it doubles as the
  `__main__` smoke test that Task 7's `__main__.py` enables).

**Interfaces:**
- Consumes: everything; the deliverable here is the human-runnable binary.
- Produces: a `README.md`, a `pyproject.toml`, and proof that
  `python -m dirsummary <dir>` works end-to-end against a hand-built tree.

- [ ] **Step 1: Write `pyproject.toml`** — `[project]` with name, version,
  `requires-python = ">=3.7"`, `dependencies = []`, and
  `[project.scripts] dirsummary = "dirsummary.cli:main"`. Keep it minimal.

- [ ] **Step 2: Write `README.md`** — a one-paragraph *what it does*, the two
  run forms:
  ```bash
  python -m dirsummary some/path
  python -m dirsummary some/path --json
  ```
  an example of each output block (paste real output from Step 3), the
  "stdlib only, no dependencies, Python 3.7+" line, and the behavior notes
  (symlinks counted not followed, broken links skipped, hidden included).

- [ ] **Step 3: Build a hand-made fixture tree and run the real binary** —
  `cd dirsummary && mkdir -p demo/{a,b,.hidden} && echo hi > demo/a/x.py &&
  echo yo > demo/b/y.txt && python -m dirsummary demo && python -m dirsummary
  demo --json` and eyeball that both outputs are clean, sane, and match what
  the tests assert. This is an **execution check, not a new test file.**

- [ ] **Step 4: Run the *whole* suite one last time** — `python -m pytest`
  from `dirsummary/` with no `-k` — everything green.

- [ ] **Step 5: Commit and leave the demo tree as untracked (or delete it
  after eyeballing — your call, but do it *after* Step 3 so the eyeball is
  honest).**

```bash
git add pyproject.toml README.md
git commit -m "docs: project packaging, README, and end-to-end smoke run"
```

---

## Notes for the implementer

- **Python 3.7 is the floor.** The test environment is 3.7.6 / pytest 5.4.2;
  do **not** use `pathlib` features or typing constructs newer than 3.7.
- **Pin numbers by hand before coding.** Every "≈ this value" in a test above
  is a placeholder you compute from the real `format_size` / real `summarize`
  output *before* asserting it — do not guess a rounding.
- **The `dict_from_collect` helper** is a test-module-local convenience
  (type → summed size); keep it in `tests/`, never in `summary.py`.
- **Commit message style** follows the `feat:` / `docs:` `chore:` prefix,
  one commit per task, each *after* its tests pass (strict TDD order:
  write-fail → implement → pass → commit).
- **Run everything from the `dirsummary/` directory** (that's where
  `conftest.py` puts the package root on `sys.path` for pytest 5.x).
