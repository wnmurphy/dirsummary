# pure, side-effect-free logic for dirsummary

import os

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

