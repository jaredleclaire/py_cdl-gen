# py_cdl-gen

A Python command-line tool that generates an **ASC CDL** (American Society of
Cinematographers Color Decision List) from two pixel-aligned reference
images — a "source" (ungraded) image and a "target" (graded) image that show
the same content with a different color grade applied.

It recovers the CDL **Slope / Offset / Power / Saturation** values that best
reproduce the target grade when applied to the source image, and writes them
out as a standard `.cc` or `.cdl` XML file.

## How it works

The ASC CDL applies color correction in two stages:

1. **SOP** (per-channel): `out = clip(in * slope + offset, 0, 1) ^ power`
2. **Sat** (cross-channel): `out = luma + saturation * (color - luma)`

Since `target = Sat(SOP(source))`, and `Sat` mixes channels via luma, fitting
SOP directly against the final target would be biased. The tool instead:

1. Fits per-channel SOP curves (via `scipy.optimize.curve_fit`) against a
   "desaturated" version of the target.
2. Refits saturation with a closed-form least-squares solve (the Sat operator
   is linear in `saturation`, so this has an exact solution).
3. Alternates steps 1–2 for a few iterations until the two operators
   converge, since desaturating the target depends on the current saturation
   estimate.

## Installation

This project is managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

This creates `.venv` with the pinned Python version and the locked
dependencies from `uv.lock`. To install the `cdl-gen` command globally
instead:

```bash
uv tool install .
```

## Usage

```bash
uv run cdl-gen source.png target.png -o output.cc
```

(`uv run python -m cdl_gen ...` also works.)

Arguments:

- `source` — path to the ungraded reference image
- `target` — path to the graded reference image (must be pixel-aligned with `source`)
- `-o, --output` — output path; use a `.cdl` extension to write a full Color
  Decision List, otherwise a standalone `.cc` Color Correction file is written
- `--id` — the `ColorCorrection` id attribute (default: `cc001`)
- `--max-samples` — max pixels sampled per channel for curve fitting (default: 200000)
- `--iterations` — number of SOP/Saturation refinement passes (default: 8)

Example output (`.cc`):

```xml
<ColorCorrection id="cc001">
    <SOPNode>
        <Slope>1.150373 0.950262 1.051911</Slope>
        <Offset>0.030453 -0.010378 0.019207</Offset>
        <Power>0.901141 0.999663 1.099944</Power>
    </SOPNode>
    <SatNode>
        <Saturation>0.698948</Saturation>
    </SatNode>
</ColorCorrection>
```

## Development

```bash
uv sync          # installs the dev dependency group (pytest) by default
uv run pytest
uv build         # builds sdist and wheel into dist/
```

Add dependencies with `uv add <pkg>` (or `uv add --dev <pkg>`) so
`pyproject.toml` and `uv.lock` stay in sync.

