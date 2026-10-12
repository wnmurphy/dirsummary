# pure, side-effect-free logic for dirsummary

import os
from dataclasses import dataclass

_UNITS = ["KB", "MB", "GB", "TB", "PB", "EB", "ZB"]


def format_size(n: int) -> str:
    """Render a byte count with binary steps, one decimal from KB up."""
    if n < 1024:
        return f"{n} B"
    value = float(n)
    for unit in _UNITS:
        value /= 1024.0
        if value < 1024.0:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} YB"


def classify(name: str, is_symlink: bool = False) -> str:
    """Return the canonical type key for a filename.

    Symlinks are always ``(symlink)``. Otherwise the extension after the last
    dot, lowercased and dotted; a leading dot or a missing extension yields
    ``(no extension)``.
    """
    if is_symlink:
        return "(symlink)"
    dot = name.rfind(".")
    if dot <= 0:
        return "(no extension)"
    ext = name[dot + 1:]
    if ext == "":
        return "(no extension)"
    return "." + ext.lower()


def _entry_size(full_path):
    """Return the link's own byte size via lstat, or None if unreadable."""
    try:
        return os.lstat(full_path).st_size
    except OSError:
        return None


def collect(path):
    """Walk *path* recursively, yielding one (type_key, size) per file/symlink.

    Symlinks are counted as their own ``(symlink)`` entry and are never
    descended into. Broken or unreadable entries are skipped rather than
    raising.
    """
    entries = []
    for dirpath, dirnames, filenames in os.walk(
        path, onerror=lambda _e: None, followlinks=False
    ):
        # Symlinks to directories appear in dirnames; count them without descent.
        for name in dirnames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                size = _entry_size(full)
                if size is not None:
                    entries.append(("(symlink)", size))
        for name in filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                size = _entry_size(full)
                if size is not None:
                    entries.append(("(symlink)", size))
            else:
                size = _entry_size(full)
                if size is not None:
                    entries.append((classify(name), size))
    return entries


@dataclass
class TypeStat:
    type: str
    count: int
    total_bytes: int


@dataclass
class Summary:
    total_files: int
    total_bytes: int
    by_type: list


def summarize(entries):
    """Collapse (type_key, size) entries into a sorted per-type summary."""
    aggregated = {}
    for key, size in entries:
        count, total = aggregated.get(key, (0, 0))
        aggregated[key] = (count + 1, total + size)
    by_type = [
        TypeStat(key, count, total) for key, (count, total) in aggregated.items()
    ]
    by_type.sort(key=lambda stat: (-stat.total_bytes, stat.type))
    total_bytes = sum(total for _, total in aggregated.values())
    return Summary(len(entries), total_bytes, by_type)


def human_lines(summary, path_label):
    """Return a list of pre-formatted output lines for the human view.

    `path_label` is kept in the signature for future use (e.g. a header line);
    the current output is just per-type rows, a separator, and a totals line.
    """
    lines = []
    for stat in summary.by_type:
        lines.append(f"{stat.count:>4}  {stat.type:<16} {format_size(stat.total_bytes):>10}")
    if summary.by_type:
        lines.append("-" * 34)
    lines.append(f"{summary.total_files} files, {format_size(summary.total_bytes)} total")
    return lines


def human_table(summary, path_label):
    """Return `human_lines` joined for printing."""
    return "\n".join(human_lines(summary, path_label))

