from __future__ import annotations

import math
import re
from collections import Counter

from .base import ScoreResult


HAWKISH_TERMS = {
    "inflation": 2,
    "price stability": 3,
    "underlying inflation": 3,
    "too high": 2,
    "upside risks": 2,
    "restrictive": 2,
    "tightening": 2,
    "raise rates": 3,
    "higher rates": 2,
    "persistent inflation": 3,
    "second-round effects": 2,
    "anchored expectations": 1,
    "vigilant": 1,
}

DOVISH_TERMS = {
    "weak growth": 3,
    "downside risks": 2,
    "support the economy": 3,
    "easing": 2,
    "rate cuts": 3,
    "lower rates": 2,
    "disinflation": 2,
    "fragmentation": 2,
    "accommodative": 2,
    "slack": 1,
    "recession": 2,
    "unemployment": 1,
    "gradual": 1,
    "uncertainty": 1,
}


def _normalized_text(*parts: str) -> str:
    return " ".join(part or "" for part in parts).lower()


def _count_terms(text: str, terms: dict[str, int]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for term, weight in terms.items():
        matches = min(3, len(re.findall(re.escape(term), text)))
        if matches:
            counts[term] = matches * weight
    return counts


class HeuristicScorer:
    mode_name = "heuristic"

    def score(self, row: dict[str, str]) -> ScoreResult:
        text = _normalized_text(row.get("Title", ""), row.get("Subtitle", ""), row.get("text", ""))
        hawkish = _count_terms(text, HAWKISH_TERMS)
        dovish = _count_terms(text, DOVISH_TERMS)
        hawkish_total = sum(hawkish.values())
        dovish_total = sum(dovish.values())
        total_signal = hawkish_total + dovish_total

        if total_signal == 0:
            signal = 0.0
        else:
            signal = (hawkish_total - dovish_total) / max(4, total_signal)

        if signal >= 0.45:
            score = 2
        elif signal >= 0.12:
            score = 1
        elif signal <= -0.45:
            score = -2
        elif signal <= -0.12:
            score = -1
        else:
            score = 0

        confidence = min(0.88, 0.40 + abs(signal) * 0.90 + math.log1p(total_signal) / 10)

        if total_signal == 0:
            rationale = "No strong policy cue was detected, so the speech is treated as neutral."
        elif signal > 0.12:
            top_terms = ", ".join(term for term, _ in hawkish.most_common(3))
            rationale = f"Hawkish cues dominate, especially: {top_terms}."
        elif signal < -0.12:
            top_terms = ", ".join(term for term, _ in dovish.most_common(3))
            rationale = f"Dovish cues dominate, especially: {top_terms}."
        else:
            rationale = "Hawkish and dovish cues are both present, so the speech is treated as balanced."

        status = "ambiguous" if abs(signal) < 0.18 else "scored"
        return ScoreResult(
            hawk_dove_score=score,
            confidence=round(confidence, 3),
            short_rationale=rationale,
            scoring_mode=self.mode_name,
            status=status,
            provider="local-heuristic",
        )
