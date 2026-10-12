# pure, side-effect-free logic for dirsummary

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

