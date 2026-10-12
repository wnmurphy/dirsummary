from dirsummary.cli import main


def test_main_human_output(tmp_path, capsys):
    (tmp_path / "a.py").write_text("x" * 1024)
    rc = main([str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert ".py" in captured.out
    assert captured.err == ""


def test_main_json_output(tmp_path, capsys):
    (tmp_path / "a.py").write_text("x" * 1024)
    rc = main([str(tmp_path), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"by_type"' in captured.out
    assert '"total_files"' in captured.out


def test_main_empty_dir(tmp_path, capsys):
    rc = main([str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "0 files" in captured.out


def test_main_defaults_to_current_dir(tmp_path, capsys, monkeypatch):
    (tmp_path / "a.py").write_text("x")
    monkeypatch.chdir(tmp_path)
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert ".py" in captured.out


def test_main_missing_path_exits_1(tmp_path, capsys):
    rc = main([str(tmp_path / "nope")])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""       # errors go to stderr, not stdout
    assert captured.err != ""


def test_main_file_not_dir_exits_1(tmp_path, capsys):
    target = tmp_path / "a.txt"
    target.write_text("hi")
    rc = main([str(target)])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert captured.err != ""
