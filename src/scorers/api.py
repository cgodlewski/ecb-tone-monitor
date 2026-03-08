from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import ScoreResult


class ApiScorer:
    mode_name = "api"

    def __init__(
        self,
        provider: str,
        model: str,
        cache_path: Path,
        daily_budget: int = 25,
        pause_seconds: float = 2.0,
        max_input_chars: int = 8000,
    ) -> None:
        self.provider = provider
        self.model = model
        self.cache_path = cache_path
        self.daily_budget = daily_budget
        self.pause_seconds = pause_seconds
        self.max_input_chars = max_input_chars
        self.calls_made = 0
        self.cache = self._load_cache()

    def _load_cache(self) -> dict[str, dict]:
        if not self.cache_path.exists():
            return {}
        return json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _save_cache(self) -> None:
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _build_prompt(self, row: dict[str, str]) -> str:
        text = (row.get("text") or "")[: self.max_input_chars]
        return (
            "You are an analyst of ECB monetary policy communication.\n"
            "Evaluate the implied monetary policy stance on this scale: -2, -1, 0, 1, 2.\n"
            "Return JSON only with keys hawk_dove_score, confidence, short_rationale.\n\n"
            f"Speaker: {row.get('Authorname', '')}\n"
            f"Date: {row.get('Date', '')}\n"
            f"Title: {row.get('Title', '')}\n"
            f"Subtitle: {row.get('Subtitle', '')}\n\n"
            f"Speech excerpt:\n{text}\n"
        )

    def _cache_key(self, row: dict[str, str]) -> str:
        raw = "|".join(
            [
                self.provider,
                self.model,
                row.get("Date", ""),
                row.get("Authorname", ""),
                row.get("Title", ""),
                (row.get("text") or "")[: self.max_input_chars],
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _request_openai_compatible(self, api_key: str, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url="https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return json.loads(body["choices"][0]["message"]["content"])

    def score(self, row: dict[str, str]) -> ScoreResult:
        cache_key = self._cache_key(row)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return ScoreResult(cached=True, **cached)

        if self.calls_made >= self.daily_budget:
            return ScoreResult(
                hawk_dove_score=None,
                confidence=0.0,
                short_rationale="Daily API budget reached.",
                scoring_mode=self.mode_name,
                status="quota_blocked",
                provider=self.provider,
            )

        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            return ScoreResult(
                hawk_dove_score=None,
                confidence=0.0,
                short_rationale="Missing GROQ_API_KEY.",
                scoring_mode=self.mode_name,
                status="quota_blocked",
                provider=self.provider,
            )

        prompt = self._build_prompt(row)
        try:
            payload = self._request_openai_compatible(api_key, prompt)
        except urllib.error.HTTPError as exc:
            status = "quota_blocked" if exc.code == 429 else "error"
            return ScoreResult(
                hawk_dove_score=None,
                confidence=0.0,
                short_rationale=f"HTTP {exc.code}: {exc.reason}",
                scoring_mode=self.mode_name,
                status=status,
                provider=self.provider,
            )
        except Exception as exc:
            return ScoreResult(
                hawk_dove_score=None,
                confidence=0.0,
                short_rationale=str(exc),
                scoring_mode=self.mode_name,
                status="error",
                provider=self.provider,
            )

        self.calls_made += 1
        time.sleep(self.pause_seconds)

        result = ScoreResult(
            hawk_dove_score=int(payload["hawk_dove_score"]),
            confidence=float(payload["confidence"]),
            short_rationale=str(payload["short_rationale"]).strip(),
            scoring_mode=self.mode_name,
            status="scored",
            provider=self.provider,
        )
        self.cache[cache_key] = {
            "hawk_dove_score": result.hawk_dove_score,
            "confidence": result.confidence,
            "short_rationale": result.short_rationale,
            "scoring_mode": result.scoring_mode,
            "status": result.status,
            "provider": result.provider,
        }
        self._save_cache()
        return result
