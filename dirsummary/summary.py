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

