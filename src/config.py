from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"


@dataclass(frozen=True)
class ScopeConfig:
    start_year: int = 2019
    end_year: int = 2023
    speakers: tuple[str, ...] = ("Christine Lagarde", "Isabel Schnabel")

    def contains_year(self, value: str) -> bool:
        year = int(value[:4])
        return self.start_year <= year <= self.end_year

    def contains_speaker(self, speaker: str) -> bool:
        return speaker in self.speakers


DEFAULT_SCOPE = ScopeConfig()


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
