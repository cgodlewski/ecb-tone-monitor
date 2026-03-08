from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoreResult:
    hawk_dove_score: int | None
    confidence: float
    short_rationale: str
    scoring_mode: str
    status: str = "scored"
    provider: str = ""
    cached: bool = False
