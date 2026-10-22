"""Command-line interface: generate an ASC CDL from two reference images."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alive_progress import alive_bar

from .cdl_writer import identity_values, write_cc, write_cdl
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
    parser.add_argument(
        "source", nargs="?", help="Path to the source (ungraded) reference image",
    )
    parser.add_argument(
        "target", nargs="?", help="Path to the target (graded) reference image",
    )
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
    parser.add_argument(
        "--no-progress", action="store_true",
        help="Disable progress bars",
    )
    parser.add_argument(
        "--identity", action="store_true",
        help=(
            "Skip fitting and write an identity (bypass) CDL with default values "
            "for troubleshooting; source and target are not needed"
        ),
    )
    args = parser.parse_args(argv)

    if args.identity:
        if args.source or args.target:
            parser.error("source and target are not used with --identity")
        return _write_and_report(args.output, *identity_values(), cc_id=args.cc_id)
    if not (args.source and args.target):
        parser.error("source and target are required unless --identity is given")

    bar_opts = dict(
        file=sys.stderr, disable=args.no_progress, enrich_print=False, title_length=14,
    )

    with alive_bar(2, title="Loading images", **bar_opts) as bar:
        bar.text = Path(args.source).name
        source = load_image(args.source)
        bar()
        bar.text = Path(args.target).name
        target = load_image(args.target)
        bar()

    if source.shape != target.shape:
        print(
            f"Error: image dimensions differ (source={source.shape}, "
            f"target={target.shape}). Images must be pixel-aligned.",
            file=sys.stderr,
        )
        return 1

    with alive_bar(args.iterations, title="Fitting CDL", **bar_opts) as bar:
        def on_iteration(i: int, sat: float) -> None:
            bar.text = f"saturation {sat:.4f}"
            bar()

        slope, offset, power, saturation = fit_cdl(
            source, target, max_samples=args.max_samples,
            iterations=args.iterations, on_iteration=on_iteration,
        )

    return _write_and_report(
        args.output, slope, offset, power, saturation, cc_id=args.cc_id,
    )


def _write_and_report(output, slope, offset, power, saturation, cc_id: str) -> int:
    out_path = Path(output)
    if out_path.suffix.lower() == ".cdl":
        write_cdl(out_path, slope, offset, power, saturation, cc_id=cc_id)
    else:
        write_cc(out_path, slope, offset, power, saturation, cc_id=cc_id)

    print(f"Slope:      {slope}")
    print(f"Offset:     {offset}")
    print(f"Power:      {power}")
    print(f"Saturation: {saturation:.6f}")
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
