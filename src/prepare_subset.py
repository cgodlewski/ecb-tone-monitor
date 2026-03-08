from __future__ import annotations

import argparse
import csv
from pathlib import Path

from config import DATA_DIR, DEFAULT_SCOPE, ScopeConfig, ensure_dirs


DEFAULT_INPUT = Path("ecb_speeches_lite.csv")
DEFAULT_OUTPUT = DATA_DIR / "ecb_subset_2019_2023_lagarde_schnabel.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a quota-friendly ECB subset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start-year", type=int, default=DEFAULT_SCOPE.start_year)
    parser.add_argument("--end-year", type=int, default=DEFAULT_SCOPE.end_year)
    parser.add_argument(
        "--speakers",
        nargs="+",
        default=list(DEFAULT_SCOPE.speakers),
        help="Speaker names to keep.",
    )
    return parser.parse_args()


def prepare_subset(input_path: Path, output_path: Path, scope: ScopeConfig) -> dict[str, int]:
    ensure_dirs([output_path.parent])
    kept = 0
    total = 0

    with input_path.open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        fieldnames = reader.fieldnames or []

        with output_path.open("w", encoding="utf-8", newline="") as dst:
            writer = csv.DictWriter(dst, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total += 1
                if not scope.contains_year(row["Date"]):
                    continue
                if not scope.contains_speaker(row["Authorname"]):
                    continue
                writer.writerow(row)
                kept += 1

    return {"total": total, "kept": kept}


def main() -> None:
    args = parse_args()
    scope = ScopeConfig(
        start_year=args.start_year,
        end_year=args.end_year,
        speakers=tuple(args.speakers),
    )
    stats = prepare_subset(args.input, args.output, scope)
    print(f"Input rows: {stats['total']}")
    print(f"Kept rows : {stats['kept']}")
    print(f"Output    : {args.output}")


if __name__ == "__main__":
    main()
