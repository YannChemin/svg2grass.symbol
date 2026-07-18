"""Converts a (simple) SVG icon into GRASS GIS's native vector symbol format.

GRASS's `d.vect icon=` does not read SVG -- it reads its own small text
grammar (VERSION/BOX/POLYGON/RING/STRING/LINE/ARC), one file per symbol,
under a `group/name` directory tree (see GRASS's `lib/symbol/README` and
e.g. `lib/symbol/symbol/extra/airport` in the GRASS source for the
reference grammar; also confirmed that `d.vect`'s `icon=` option validates
against a hardcoded list built only from `$GISBASE/etc/symbol` at parse
time -- see `display/d.vect/main.c`'s `icon_files()` -- so a converted
symbol must actually be installed there, not just in a mapset, to be
usable from `d.vect`'s CLI). GRASS 8.6 has no SVG symbol support at all.

Scope, deliberately kept simple:
  - SVG path commands supported: M/m L/l H/h V/v C/c A/a Z/z. No S/Q/T
    (smooth-shorthand) support -- add it if you hit an icon that needs it.
  - Cubic beziers (C) and elliptical arcs (A) inside a *path* are flattened
    to straight-line segments (sampled), not re-expressed as GRASS ARC --
    simpler and correct at icon scale, at the cost of an exact curve match.
  - <circle> elements map directly and exactly to GRASS's native ARC
    primitive (mirrors the reference example: `ARC 0 0 2 360 0 C`).
  - Fill resolution: an element (or an ancestor <svg>) with fill="none"
    produces an unfilled GRASS STRING; anything else produces a filled
    GRASS POLYGON. COLOR/FCOLOR are deliberately left unset so `d.vect
    color=`/`fill_color=` still control the rendered color at draw time.
  - Multiple disjoint subpaths in one filled <path> become separate
    POLYGONs (not rings-as-holes of one POLYGON) -- correct for disjoint
    glyph shapes, but mis-renders a genuinely nested hole (e.g. a ring
    shape, or a circle with a punched-out rectangle) as filled/outlined
    rather than a true see-through gap. Usually still reads fine as an
    icon at symbol scale; a known, deliberately-accepted simplification.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_NUM_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")
_CMD_LETTERS = set("MmLlHhVvCcAaZz")
_ARG_COUNTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "A": 7, "Z": 0}
BEZIER_SEGMENTS = 12
ARC_SEGMENTS = 16


def _tokenize(d: str) -> list[str]:
    tokens = []
    i = 0
    while i < len(d):
        ch = d[i]
        if ch in _CMD_LETTERS:
            tokens.append(ch)
            i += 1
        elif ch.isspace() or ch == ",":
            i += 1
        else:
            m = _NUM_RE.match(d, i)
            if not m:
                raise ValueError(f"Unparseable SVG path at position {i}: {d[i:i+20]!r}")
            tokens.append(m.group(0))
            i = m.end()
    return tokens


def _flatten_cubic(p0, p1, p2, p3, n=BEZIER_SEGMENTS):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def _flatten_arc(p0, rx, ry, phi_deg, large_arc, sweep, p1, n=ARC_SEGMENTS):
    """SVG elliptical-arc endpoint parameterization -> sampled points.
    Standard construction from the SVG 1.1 spec, appendix F.6."""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [p1]

    phi = math.radians(phi_deg)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)

    dx2, dy2 = (x1 - x2) / 2, (y1 - y2) / 2
    x1p = cos_phi * dx2 + sin_phi * dy2
    y1p = -sin_phi * dx2 + cos_phi * dy2

    rx, ry = abs(rx), abs(ry)
    lam = (x1p**2) / (rx**2) + (y1p**2) / (ry**2)
    if lam > 1:
        scale = math.sqrt(lam)
        rx, ry = rx * scale, ry * scale

    sign = -1 if large_arc == sweep else 1
    num = rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2
    den = rx**2 * y1p**2 + ry**2 * x1p**2
    co = sign * math.sqrt(max(num, 0) / den) if den else 0
    cxp = co * (rx * y1p) / ry
    cyp = -co * (ry * x1p) / rx

    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        length = math.sqrt(ux**2 + uy**2) * math.sqrt(vx**2 + vy**2)
        ang = math.acos(max(-1, min(1, dot / length))) if length else 0
        return ang if (ux * vy - uy * vx) >= 0 else -ang

    theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dtheta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    points = []
    for i in range(1, n + 1):
        t = theta1 + dtheta * i / n
        x = cx + rx * math.cos(t) * cos_phi - ry * math.sin(t) * sin_phi
        y = cy + rx * math.cos(t) * sin_phi + ry * math.sin(t) * cos_phi
        points.append((x, y))
    points[-1] = p1  # avoid float noise at the shared endpoint with the next segment
    return points


@dataclass
class Subpath:
    points: list[tuple[float, float]]
    closed: bool


def parse_path(d: str) -> list[Subpath]:
    """Parse an SVG path `d` attribute into a list of flattened Subpaths
    (absolute coordinates, curves/arcs already sampled to line segments)."""
    tokens = _tokenize(d)
    subpaths: list[Subpath] = []
    cur: list[tuple[float, float]] = []
    x = y = 0.0
    start_x = start_y = 0.0
    last_cmd = ""
    i = 0

    def flush(closed: bool):
        nonlocal cur
        if len(cur) >= 2:
            subpaths.append(Subpath(cur, closed))
        cur = []

    while i < len(tokens):
        tok = tokens[i]
        if tok in _CMD_LETTERS:
            cmd = tok
            i += 1
        else:
            if not last_cmd:
                raise ValueError("Path data starts with a number, not a command")
            # bare numbers repeat the previous command (M repeats as L)
            cmd = {"M": "L", "m": "l"}.get(last_cmd, last_cmd)

        upper = cmd.upper()
        relative = cmd.islower()
        nargs = _ARG_COUNTS[upper]
        args = [float(tokens[i + k]) for k in range(nargs)]
        i += nargs

        if upper == "Z":
            x, y = start_x, start_y
            flush(closed=True)
        elif upper == "M":
            flush(closed=False)
            nx, ny = args
            if relative:
                nx, ny = x + nx, y + ny
            x, y = nx, ny
            start_x, start_y = x, y
            cur = [(x, y)]
        elif upper == "L":
            nx, ny = args
            if relative:
                nx, ny = x + nx, y + ny
            x, y = nx, ny
            cur.append((x, y))
        elif upper == "H":
            nx = args[0]
            x = x + nx if relative else nx
            cur.append((x, y))
        elif upper == "V":
            ny = args[0]
            y = y + ny if relative else ny
            cur.append((x, y))
        elif upper == "C":
            x1, y1, x2, y2, x3, y3 = args
            if relative:
                x1, y1, x2, y2, x3, y3 = x + x1, y + y1, x + x2, y + y2, x + x3, y + y3
            cur.extend(_flatten_cubic((x, y), (x1, y1), (x2, y2), (x3, y3)))
            x, y = x3, y3
        elif upper == "A":
            rx, ry, phi, large_arc, sweep, ex, ey = args
            if relative:
                ex, ey = x + ex, y + ey
            cur.extend(_flatten_arc((x, y), rx, ry, phi, large_arc, sweep, (ex, ey)))
            x, y = ex, ey

        last_cmd = cmd

    flush(closed=False)
    return subpaths


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _resolve_fill(elem_fill: str | None, inherited_none: bool) -> bool:
    """Returns True if this element is unfilled (fill:none), given its own
    fill attribute and whether an ancestor declared fill=none."""
    if elem_fill is not None:
        return elem_fill.strip().lower() == "none"
    return inherited_none


@dataclass
class Shape:
    subpaths: list[Subpath]
    filled: bool
    is_circle: bool = False
    circle: tuple[float, float, float] | None = None  # cx, cy, r


def extract_shapes(svg_text: str) -> tuple[float, float, list[Shape]]:
    """Returns (width, height, shapes) in SVG user-space units."""
    root = ET.fromstring(svg_text)
    view_box = root.get("viewBox")
    if view_box:
        _, _, w, h = (float(v) for v in view_box.split())
    else:
        w, h = float(root.get("width", 24)), float(root.get("height", 24))

    root_fill_none = (root.get("fill") or "").strip().lower() == "none"
    shapes: list[Shape] = []

    for elem in root.iter():
        tag = _local(elem.tag)
        if tag == "path":
            d = elem.get("d")
            if not d:
                continue
            unfilled = _resolve_fill(elem.get("fill"), root_fill_none)
            shapes.append(Shape(subpaths=parse_path(d), filled=not unfilled))
        elif tag == "circle":
            cx, cy, r = float(elem.get("cx")), float(elem.get("cy")), float(elem.get("r"))
            unfilled = _resolve_fill(elem.get("fill"), root_fill_none)
            shapes.append(Shape(subpaths=[], filled=not unfilled, is_circle=True, circle=(cx, cy, r)))

    return w, h, shapes


def _to_symbol_space(x: float, y: float, w: float, h: float) -> tuple[float, float]:
    """SVG space (origin top-left, y-down) -> GRASS symbol space (origin
    centered, y-up), matching GRASS's own convention ("Origin of symbol is
    0,0")."""
    return x - w / 2, h / 2 - y


def convert_svg_to_symbol(svg_text: str) -> str:
    """Convert an SVG icon's text content into a GRASS vector symbol file's
    text content (the format read by `d.vect icon=` / `lib/symbol`)."""
    w, h, shapes = extract_shapes(svg_text)
    lines = ["VERSION 1.0", f"BOX {-w/2:.4f} {-h/2:.4f} {w/2:.4f} {h/2:.4f}"]

    for shape in shapes:
        if shape.is_circle:
            cx, cy, r = shape.circle
            gx, gy = _to_symbol_space(cx, cy, w, h)
            block = ["POLYGON" if shape.filled else "STRING"]
            if shape.filled:
                block.append(" RING")
                block.append(f"  ARC {gx:.4f} {gy:.4f} {r:.4f} 360 0 C")
                block.append(" END")
            else:
                block.append(f" ARC {gx:.4f} {gy:.4f} {r:.4f} 360 0 C")
            block.append("END")
            lines.extend(block)
            continue

        if shape.filled:
            lines.append("POLYGON")
            for sub in shape.subpaths:
                lines.append(" RING")
                lines.append("  LINE")
                for x, y in sub.points:
                    gx, gy = _to_symbol_space(x, y, w, h)
                    lines.append(f"   {gx:.4f} {gy:.4f}")
                lines.append("  END")
                lines.append(" END")
            lines.append("END")
        else:
            for sub in shape.subpaths:
                lines.append("STRING")
                lines.append(" LINE")
                pts = list(sub.points)
                if sub.closed and pts and pts[0] != pts[-1]:
                    pts = pts + [pts[0]]
                for x, y in pts:
                    gx, gy = _to_symbol_space(x, y, w, h)
                    lines.append(f"  {gx:.4f} {gy:.4f}")
                lines.append(" END")
                lines.append("END")

    lines.append("")
    return "\n".join(lines)
