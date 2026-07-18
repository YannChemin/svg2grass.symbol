"""Command-line entry point.

Usage:
    svg2grasssymbol input.svg output_symbol_file
    svg2grasssymbol input.svg              # writes to stdout
"""

from __future__ import annotations

import argparse
import sys

from svg2grasssymbol.converter import convert_svg_to_symbol


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="svg2grasssymbol")
    parser.add_argument("input_svg", help="path to the source SVG file")
    parser.add_argument(
        "output", nargs="?", default=None,
        help="path to write the GRASS symbol file to (default: stdout)",
    )
    args = parser.parse_args(argv)

    with open(args.input_svg, encoding="utf-8") as fh:
        svg_text = fh.read()

    symbol_text = convert_svg_to_symbol(svg_text)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(symbol_text)
    else:
        sys.stdout.write(symbol_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
