"""Command-line interface: generate an ASC CDL from two reference images."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cdl_writer import write_cc, write_cdl
from .fitting import fit_cdl
from .io_utils import load_image


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cdl_gen",
        description=(
            "Generate an ASC CDL (.cc / .cdl) from two pixel-aligned reference "
            "images that share the same content but different color grading."
        ),
    )
    parser.add_argument("source", help="Path to the source (ungraded) reference image")
    parser.add_argument("target", help="Path to the target (graded) reference image")
    parser.add_argument(
        "-o", "--output", default="output.cc",
        help="Output CDL file path (.cc or .cdl). Default: output.cc",
    )
    parser.add_argument(
        "--id", default="cc001", dest="cc_id",
        help="ColorCorrection id attribute written to the output file",
    )
    parser.add_argument(
        "--max-samples", type=int, default=200_000,
        help="Max pixel samples used for SOP curve fitting (default: 200000)",
    )
    parser.add_argument(
        "--iterations", type=int, default=8,
        help="Number of SOP/Saturation refinement passes (default: 8)",
    )
    args = parser.parse_args(argv)

    source = load_image(args.source)
    target = load_image(args.target)

    if source.shape != target.shape:
        print(
            f"Error: image dimensions differ (source={source.shape}, "
            f"target={target.shape}). Images must be pixel-aligned.",
            file=sys.stderr,
        )
        return 1

    slope, offset, power, saturation = fit_cdl(
        source, target, max_samples=args.max_samples, iterations=args.iterations
    )

    out_path = Path(args.output)
    if out_path.suffix.lower() == ".cdl":
        write_cdl(out_path, slope, offset, power, saturation, cc_id=args.cc_id)
    else:
        write_cc(out_path, slope, offset, power, saturation, cc_id=args.cc_id)

    print(f"Slope:      {slope}")
    print(f"Offset:     {offset}")
    print(f"Power:      {power}")
    print(f"Saturation: {saturation:.6f}")
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
