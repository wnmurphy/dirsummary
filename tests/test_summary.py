import os
from collections import defaultdict

from dirsummary.summary import classify, collect, format_size, summarize


def sizes_by_type(entries):
    """Test helper: collapse (type_key, size) entries into {type_key: total_size}."""
    out = defaultdict(int)
    for key, size in entries:
        out[key] += size
    return out


def test_format_size_bytes():
    assert format_size(0) == "0 B"
    assert format_size(1) == "1 B"
    assert format_size(1023) == "1023 B"


def test_format_size_kb_and_up():
    assert format_size(1024) == "1.0 KB"
    assert format_size(12576) == "12.3 KB"          # 12576/1024 = 12.305 -> 12.3
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.0 GB"


def test_classify_extensions_case_insensitive():
    assert classify("a.py") == ".py"
    assert classify("a.PNG") == ".png"
    assert classify("archive.tar.gz") == ".gz"       # last extension wins


def test_classify_no_extension():
    assert classify("Makefile") == "(no extension)"
    assert classify(".gitignore") == "(no extension)"
    assert classify("a.") == "(no extension)"


def test_classify_symlink():
    assert classify("anything", is_symlink=True) == "(symlink)"


def test_collect_basic_recurses(tmp_path):
    (tmp_path / "a.py").write_text("x" * 100)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("y" * 50)
    sizes = sizes_by_type(collect(str(tmp_path)))
    assert sizes[".py"] == 100
    assert sizes[".txt"] == 50


def test_collect_includes_hidden_files(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules\n")
    entries = collect(str(tmp_path))
    assert entries == [("(no extension)", len("node_modules\n"))]


def test_collect_counts_symlink_to_file_not_target(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("hi")
    (tmp_path / "link").symlink_to(target)
    types = [k for k, _ in collect(str(tmp_path))]
    assert types.count("(symlink)") == 1
    assert types.count(".txt") == 1


def test_collect_symlink_to_dir_counted_once_not_descended(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "c.py").write_text("z")
    (tmp_path / "sublink").symlink_to(str(real))
    entries = collect(str(tmp_path))
    assert entries.count((".py", 1)) == 1
    assert sum(1 for k, _ in entries if k == "(symlink)") == 1


def test_collect_broken_symlink_does_not_crash(tmp_path):
    (tmp_path / "broken").symlink_to(str(tmp_path / "does-not-exist"))
    entries = collect(str(tmp_path))     # must not raise
    assert any(k == "(symlink)" for k, _ in entries)


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
        (".txt", 1, 300),
        (".py", 2, 150),
    ]


def test_summarize_tie_break_name_ascending():
    entries = [(".z", 10), (".a", 10)]
    s = summarize(entries)
    assert [t.type for t in s.by_type] == [".a", ".z"]

