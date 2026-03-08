from __future__ import annotations

import argparse
import csv
from pathlib import Path

from config import DATA_DIR, LOGS_DIR, ensure_dirs
from scorers import ApiScorer, HeuristicScorer
from scorers.base import ScoreResult


DEFAULT_INPUT = DATA_DIR / "ecb_subset_2019_2023_lagarde_schnabel.csv"
DEFAULT_OUTPUT = DATA_DIR / "ecb_subset_scored.csv"
DEFAULT_CACHE = DATA_DIR / "api_cache.json"
DEFAULT_ERRORS = LOGS_DIR / "scoring_errors.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score ECB speeches with a quota-safe pipeline.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mode", choices=["heuristic", "hybrid", "api"], default="hybrid")
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--max-api-calls", type=int, default=25)
    parser.add_argument("--api-provider", default="groq")
    parser.add_argument("--api-model", default="llama-3.1-8b-instant")
    parser.add_argument("--ambiguity-threshold", type=float, default=0.60)
    return parser.parse_args()


def load_existing_rows(output_path: Path) -> dict[str, dict[str, str]]:
    if not output_path.exists():
        return {}
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["speech_id"]: row for row in reader}


def build_speech_id(row: dict[str, str]) -> str:
    return "|".join([row.get("Date", ""), row.get("Authorname", ""), row.get("Title", "")])


def fallback_result(base: ScoreResult, api_result: ScoreResult) -> ScoreResult:
    return ScoreResult(
        hawk_dove_score=base.hawk_dove_score,
        confidence=base.confidence,
        short_rationale=f"{base.short_rationale} API fallback: {api_result.short_rationale}",
        scoring_mode="hybrid",
        status="scored_fallback",
        provider=f"{base.provider}+fallback",
    )


def choose_result(
    row: dict[str, str],
    mode: str,
    heuristic: HeuristicScorer,
    api: ApiScorer | None,
    threshold: float,
) -> tuple[ScoreResult, ScoreResult | None]:
    heuristic_result = heuristic.score(row)
    if mode == "heuristic":
        return heuristic_result, None
    if mode == "api":
        return (api.score(row) if api else heuristic_result), None
    if heuristic_result.confidence >= threshold and heuristic_result.status == "scored":
        return heuristic_result, None
    if api is None:
        return heuristic_result, None
    api_result = api.score(row)
    if api_result.status == "scored":
        api_result.scoring_mode = "hybrid"
        return api_result, None
    return fallback_result(heuristic_result, api_result), api_result


def write_rows(rows: list[dict[str, str]], output_path: Path) -> None:
    if not rows:
        return
    ensure_dirs([output_path.parent])
    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_error(row: dict[str, str], output_path: Path) -> None:
    ensure_dirs([output_path.parent])
    exists = output_path.exists()
    with output_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    args = parse_args()
    ensure_dirs([DATA_DIR, LOGS_DIR])

    heuristic = HeuristicScorer()
    api = None
    if args.mode in {"hybrid", "api"}:
        api = ApiScorer(
            provider=args.api_provider,
            model=args.api_model,
            cache_path=DEFAULT_CACHE,
            daily_budget=args.max_api_calls,
        )

    existing = load_existing_rows(args.output)
    rows_out: list[dict[str, str]] = []
    processed = 0

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            speech_id = build_speech_id(row)
            if speech_id in existing:
                rows_out.append(existing[speech_id])
                continue

            result, api_issue = choose_result(row, args.mode, heuristic, api, args.ambiguity_threshold)
            output_row = dict(row)
            output_row["speech_id"] = speech_id
            output_row["hawk_dove_score"] = "" if result.hawk_dove_score is None else str(result.hawk_dove_score)
            output_row["confidence"] = f"{result.confidence:.3f}"
            output_row["short_rationale"] = result.short_rationale
            output_row["scoring_mode"] = result.scoring_mode
            output_row["scoring_status"] = result.status
            output_row["provider"] = result.provider
            rows_out.append(output_row)
            processed += 1

            issue = api_issue if api_issue is not None else (result if result.status in {"error", "quota_blocked"} else None)
            if issue is not None:
                append_error(
                    {
                        "speech_id": speech_id,
                        "date": row.get("Date", ""),
                        "speaker": row.get("Authorname", ""),
                        "title": row.get("Title", ""),
                        "status": issue.status,
                        "reason": issue.short_rationale,
                    },
                    DEFAULT_ERRORS,
                )
                if issue.status == "quota_blocked" and args.mode == "api":
                    write_rows(rows_out, args.output)
                    print("Stopped on API quota.")
                    print(f"Saved partial output to: {args.output}")
                    return

            if processed % args.save_every == 0:
                write_rows(rows_out, args.output)

    write_rows(rows_out, args.output)
    print(f"Saved scored dataset to: {args.output}")


if __name__ == "__main__":
    main()
