# Installing svg2grasssymbol

## The converter itself

Pure Python standard library, no dependencies.

```
pip install .
```

or just drop `svg2grasssymbol/converter.py` into your own project -- it
has no dependency on the rest of this package.

For development:

```
pip install -e .
pytest tests/
```

## Making a converted symbol usable in GRASS

GRASS symbol files are plain text, one file per symbol, and GRASS looks
for them in two places:

```
$GISBASE/etc/symbol/<group>/<name>
<mapset>/symbol/<group>/<name>
```

**Important**: `d.vect`'s `icon=` option is validated against a fixed
list built *only* from `$GISBASE/etc/symbol` at argument-parsing time
(see `display/d.vect/main.c`'s `icon_files()` in the GRASS source). A
symbol placed only in a mapset's `symbol/` directory will be rejected by
the CLI with `Value <group/name> out of range for parameter <icon>` even
though the lower-level reader would find it. **To use a converted symbol
from `d.vect` (or from a GUI/addon built on top of it), install it under
`$GISBASE/etc/symbol/<group>/<name>`.**

Find your `$GISBASE`:

```
grass --config path
```

Then, for a symbol group of your choosing (e.g. `myicons`):

```
mkdir -p "$(grass --config path)/etc/symbol/myicons"
svg2grasssymbol my_icon.svg "$(grass --config path)/etc/symbol/myicons/my_icon"
```

(GRASS symbol files have no file extension -- follow that convention so
`d.vect`'s symbol scanner picks the file up correctly.)

Use it:

```
d.vect map=your_map icon=myicons/my_icon size=20
```

## Verifying a conversion

SVG icons with beziers/arcs won't always convert exactly -- always
render and look at the output before trusting it in production maps.
A quick way, using GRASS's non-interactive cairo renderer:

```bash
grass --tmp-project XY --exec bash -c '
  echo "0|0" | v.in.ascii input=- output=testpt separator=pipe \
    columns="x double precision, y double precision"
  g.region n=15 s=-15 e=15 w=-15 res=1
  export GRASS_RENDER_IMMEDIATE=cairo
  export GRASS_RENDER_FILE=/tmp/symbol_check.png
  export GRASS_RENDER_WIDTH=200
  export GRASS_RENDER_HEIGHT=200
  export GRASS_RENDER_BACKGROUNDCOLOR=FFFFFF
  d.vect map=testpt icon=myicons/my_icon size=150 color=0:0:0 fill_color=180:180:220
'
```

Then open `/tmp/symbol_check.png` and compare it against the source SVG.
