"""'Spot the scam' quiz: content from `seed/quiz/*.json`, validated once at load and scored only on the server.

Answers and explanations stay here until the user submits, so a score can't be read off the page.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from backend.config import ROOT
from backend.schemas import Lang, QuizAnswer, QuizId, QuizItem, QuizResponse, QuizResult

QUIZ_DIR = ROOT / 'seed' / 'quiz'
FALLBACK_LANG = 'en'  # ta, te, kn and bn have no set yet; English beats an error
SOURCE_NOTE = 'Examples written by us from real scam patterns (SEBI, I4C advisories)'


class SeedItem(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    id: Annotated[str, StringConstraints(pattern=r'^q[1-9][0-9]?$')]
    text: Annotated[str, StringConstraints(min_length=20, max_length=600)]
    answer: QuizAnswer
    why: Annotated[str, StringConstraints(min_length=20, max_length=450)]
    pattern: Annotated[str, StringConstraints(pattern=r'^[a-z][a-z_]*$')]
    difficulty: Literal['easy', 'medium', 'hard']


class QuizSet(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    quiz_id: QuizId
    lang: Lang
    source_note: str
    card_title: str  # "{score}" and "{total}" are filled in per result
    # The answer map accepts at most 50 keys, so a longer set could never be fully answered.
    items: Annotated[list[SeedItem], Field(min_length=2, max_length=50)]

    @model_validator(mode='after')
    def _consistent(self) -> QuizSet:
        if not self.quiz_id.startswith(f'q_{self.lang}_v'):
            raise ValueError(f'{self.quiz_id} does not match lang {self.lang}')
        if self.source_note != SOURCE_NOTE:
            raise ValueError('Every quiz file carries the same source note')
        ids = [item.id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError('Item IDs must be unique within a quiz')
        if {item.answer for item in self.items} != {'scam', 'genuine'}:
            raise ValueError('A quiz needs both scam and genuine items')
        if '{score}' not in self.card_title or '{total}' not in self.card_title:
            raise ValueError('card_title needs {score} and {total}')
        self.title(0, 0)  # any other brace would raise at answer time; fail at load instead
        return self

    @property
    def version(self) -> int:
        return int(self.quiz_id.rsplit('_v', 1)[1])

    def title(self, score: int, total: int) -> str:
        return self.card_title.format(score=score, total=total)


@dataclass(frozen=True)
class Bank:
    by_id: Mapping[str, QuizSet]
    by_lang: Mapping[str, QuizSet]


@lru_cache(maxsize=1)
def bank() -> Bank:
    by_id: dict[str, QuizSet] = {}
    for file in sorted(QUIZ_DIR.glob('*.json')):
        quiz = QuizSet.model_validate_json(file.read_bytes())
        if quiz.quiz_id in by_id:
            raise ValueError(f'{quiz.quiz_id} appears in two files')
        by_id[quiz.quiz_id] = quiz
    # Serve the newest version per language; older IDs stay scorable for anyone mid-quiz across a deploy.
    by_lang = {quiz.lang: quiz for quiz in sorted(by_id.values(), key=lambda q: q.version)}
    if FALLBACK_LANG not in by_lang:
        raise ValueError('The English quiz is missing, and other languages fall back to it')
    return Bank(by_id, by_lang)


def for_lang(lang: str) -> QuizSet:
    sets = bank().by_lang
    return sets.get(lang) or sets[FALLBACK_LANG]


def by_id(quiz_id: str) -> QuizSet | None:
    return bank().by_id.get(quiz_id)


def public(quiz: QuizSet) -> QuizResponse:
    """What the browser gets before answering: the messages only, never `answer` or `why`."""
    return QuizResponse(quiz_id=quiz.quiz_id, items=[QuizItem(id=item.id, text=item.text) for item in quiz.items])


def score(quiz: QuizSet, answers: Mapping[str, str]) -> tuple[int, list[QuizResult]]:
    # Unknown IDs are ignored and missing ones count as wrong, so `total` is always the quiz's length.
    results = [QuizResult(id=item.id, correct=answers.get(item.id) == item.answer, answer=item.answer, why=item.why)
               for item in quiz.items]
    return sum(result.correct for result in results), results
