"""CLI entry point: argparse → validation → output."""

import argparse
import os
import sys
from pathlib import Path

from dirsummary.summary import collect, human_table, render_json, summarize


def main(argv=None):
    """Parse argv, walk the tree, and print the summary. Returns exit code."""
    parser = argparse.ArgumentParser(
        prog="dirsummary",
        description="Summarise a directory: per-type file counts and sizes.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output JSON instead of the human-readable table",
    )
    args = parser.parse_args(argv)
    path = args.path

    if not os.path.exists(path):
        print(f"dirsummary: no such directory: {path}", file=sys.stderr)
        return 1
    if not os.path.isdir(path):
        print(f"dirsummary: not a directory: {path}", file=sys.stderr)
        return 1

    summary = summarize(collect(path))
    path_label = str(Path(path).resolve())

    if args.json:
        print(render_json(summary, path_label))
    else:
        print(human_table(summary, path_label))
    return 0


if __name__ == "__main__":
    sys.exit(main())
