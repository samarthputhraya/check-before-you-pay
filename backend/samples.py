"""Stub responses built from `examples/*.json`, so every client can build against the contract today.

Role B replaces `sample_check` with the real pipeline. Every stub is marked with the `X-Sample` header.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from backend.config import EXAMPLES_DIR
from backend.schemas import (
    CheckResponse, CheckView, QuizAnswerResponse, QuizResponse, Share, StatsResponse,
)


@lru_cache(maxsize=None)
def _example(name: str) -> dict[str, Any]:
    return json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def share_url(base: str, check_id: str, anon_id: str | None) -> str:
    url = f"{base}/c/{check_id}"
    return f"{url}?ref={anon_id}" if anon_id else url


def sample_check(*, check_id: str, lang: str, base: str, anon_id: str, latency_ms: int) -> CheckResponse:
    data = dict(_example("check_response"))
    data.update(check_id=check_id, lang=lang, latency_ms=latency_ms,
                share={**data["share"], "url": share_url(base, check_id, anon_id)})
    return CheckResponse.model_validate(data)


def sample_view(*, check_id: str, base: str) -> CheckView:
    data = {k: v for k, v in _example("check_response").items() if k != "transcript"}
    data.update(check_id=check_id, share={**data["share"], "url": share_url(base, check_id, None)})
    return CheckView.model_validate(data)


def sample_quiz(lang: str) -> QuizResponse:
    data = dict(_example("quiz_response"))
    data["quiz_id"] = f"q_{lang}_v1"
    return QuizResponse.model_validate(data)


def sample_quiz_answer(*, base: str, anon_id: str) -> QuizAnswerResponse:
    data = dict(_example("quiz_answer_response"))
    data["share"] = Share(url=f"{base}/quiz?ref={anon_id}", card_title=data["share"]["card_title"]).model_dump()
    return QuizAnswerResponse.model_validate(data)


def sample_stats() -> StatsResponse:
    return StatsResponse.model_validate(_example("stats_response"))
