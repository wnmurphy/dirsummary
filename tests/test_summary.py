from dirsummary.summary import format_size


def test_format_size_bytes():
    assert format_size(0) == "0 B"
    assert format_size(1) == "1 B"
    assert format_size(1023) == "1023 B"


def test_format_size_kb_and_up():
    assert format_size(1024) == "1.0 KB"
    assert format_size(12576) == "12.3 KB"          # 12576/1024 = 12.305 -> 12.3
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.0 GB"
