# Card generator

This project generates 3D-printable cards using OpenSCAD and a simple Python helper script.

## Contents

- `generate.py` — batch-generate card STL files from a list of names.
- `template_card.scad` — creates the base template card shape.
- `card.scad` — imports the template card and embosses text for a final card.

## Requirements

- Python 3
- OpenSCAD
- BOSL2 library available to OpenSCAD (for `textmetrics` support)

## Using `generate.py`

`generate.py` reads a newline-separated list of names <FILENAME> and generates one `.stl` card per name.

### Basic usage

```bash
python generate.py <FILENAME>
```

### Common options

- `--openscad_path PATH` — path to the OpenSCAD executable
- `-j, --cpu_threads N` — number of parallel threads to use
- `-f, --force_generate_template` — regenerate `template_card.stl` even if it already exists
- `--only_generate_template` — generate only `template_card.stl` and exit
- `--openscad_quiet` — hide OpenSCAD output
- `-o, --outdir DIR` — output directory for generated STL files
- `--out_use_subdir` — split output into subdirectories for large batches
- `--outdir_by_letter` — sort output into subdirectories by the first letter of each name
- `--out_subdir_count N` — maximum files per generated subdirectory
- `--resolution N` — OpenSCAD polygon resolution (`$fn`) for generated models
- `--text_resolution N` — OpenSCAD polygon resolution for embossed text only
- `-n, --noexec` — print commands without executing them
- `--no-summary` — suppress the final summary report
- `-v, --verbose` — print additional debug output
- `-q, --quiet` — only show warnings and errors

### Example

```bash
python generate.py <FILENAME> -j 4 -o gen
```

To increase the OpenSCAD polygon resolution for both template and card generation:

```bash
python generate.py <FILENAME> --resolution 128 -o gen
```

This will generate `template_card.stl` if needed, then create a card STL in `./gen/` for every unique name in `<FILENAME>`.

## Using `template_card.scad` directly

`template_card.scad` defines the base card geometry with a rounded border ridge.

### Generate the template STL

```bash
openscad -o template_card.stl template_card.scad
```

### Customization

OpenSCAD allows top-level variables to be overridden from the command line with `-D`.
For example, to change the card height and width:

```bash
openscad -o template_card.stl -D card_h=40 -D card_l=120 template_card.scad
```

Common overrides:

- `card_h`, `card_l`, `card_d` — card height, length, and thickness
- `ridge_w`, `ridge_h` — raised border width and height
- `generate_hole` — whether to subtract a hole from the card
- `hole_offset`, `hole_depth`, `hole_radius` — hole placement and size
- `resolution` — polygon resolution used by OpenSCAD (`$fn`)

## Using `card.scad` directly

`card.scad` imports the generated `template_card.stl` and creates embossed text on top.

### Generate a single card STL

```bash
openscad -o card.stl card.scad
```

### Customization

OpenSCAD allows top-level variables to be overridden from the command line with `-D`.
For example, to set the embossed text directly:

```bash
openscad -o card.stl --enable textmetrics -D 'template_file="gen/template_card.stl"' -D 'text="Jane Doe"' card.scad
```

Common overrides:

- `template_file` — the path to the template STL file
- `text` — the text printed on the card
- `font` — the font used for embossing
- `text_margin` — margin between text and card edges
- `sample_size`, `max_font_size`, `emboss_height` — text sizing and emboss depth
- `generate_hole`, `hole_offset`, `hole_depth`, `hole_radius` — optional hole settings
- `resolution` — polygon resolution used by OpenSCAD (`$fn`)

### Workflow

1. Generate `template_card.stl` from `template_card.scad`.
2. Verify `card.scad` references the correct `template_file`.
3. Run OpenSCAD to export `card.stl`.

## Notes

- `card.scad` depends on `template_card.stl` being available.
- If you want to batch-create cards, use `generate.py` instead of manual OpenSCAD steps.

## License

This project is licensed under the GNU General Public License v3.0.
