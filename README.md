# svg2grasssymbol

Converts simple SVG icons into [GRASS GIS](https://grass.osgeo.org/)'s
native vector symbol format, the small text grammar read by `d.vect
icon=` (`VERSION`/`BOX`/`POLYGON`/`RING`/`STRING`/`LINE`/`ARC`). GRASS has
no SVG symbol support at all, so this fills that gap for anyone who wants
to render SVG-designed icons as GRASS point/centroid symbols.

Verified against GRASS 8.6: `d.vect`'s `icon=` option only accepts symbols
already installed under `$GISBASE/etc/symbol/<group>/<name>` (a symbol
placed in a mapset's own `symbol/` directory is found by the low-level
reader but rejected by the CLI parser's option validation first) -- see
INSTALL.md.

## What it handles

- SVG path commands `M/m L/l H/h V/v C/c S/s A/a Z/z`. No `Q`/`T`
  (quadratic curve) support yet.
- Cubic Bézier curves and elliptical arcs inside a path are flattened to
  sampled straight-line segments, not re-expressed as GRASS's native
  `ARC` -- simpler, and correct enough at icon scale, at the cost of an
  exact curve match.
- `<circle>` elements map directly and exactly to GRASS's native `ARC`
  primitive.
- `fill="none"` (on the element itself, or inherited from the `<svg>`
  root) produces an unfilled GRASS `STRING`; anything else produces a
  filled `POLYGON`. `COLOR`/`FCOLOR` are deliberately left unset in the
  output so `d.vect color=`/`fill_color=` still control the rendered
  color at draw time.

## Known limitation

Multiple disjoint subpaths within one filled `<path>` become separate
`POLYGON`s rather than rings-as-holes of a single `POLYGON`. This is
correct for ordinary disjoint glyph shapes, but a *genuinely* nested hole
(e.g. a ring, or a circle with a rectangular hole punched out of it, like
Mapbox Maki's "roadblock" icon) renders as filled/outlined instead of a
true see-through gap. It still generally reads fine as an icon at symbol
scale -- this is a deliberately accepted simplification, not an
oversight.

## Usage

```
svg2grasssymbol input.svg output_symbol_file
svg2grasssymbol input.svg                    # writes to stdout
```

Or as a library:

```python
from svg2grasssymbol import convert_svg_to_symbol

with open("input.svg") as f:
    svg_text = f.read()

symbol_text = convert_svg_to_symbol(svg_text)
```

See INSTALL.md for how to get a converted symbol actually usable from
`d.vect icon=`.

## Testing

```
pytest tests/
```

No network access or GRASS installation is required to run the tests --
they only exercise the pure SVG-to-grammar conversion. Actually rendering
the output through GRASS (recommended before trusting a conversion) does
require a GRASS installation; see INSTALL.md.

## License

Public domain / [Unlicense](https://unlicense.org) -- see `LICENSE`.
