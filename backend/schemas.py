"""Request and response models. These mirror `API_CONTRACT.md` exactly; change both together."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool, StringConstraints

Lang = Literal["en", "hi", "mr", "ta", "te", "kn", "bn", "hinglish"]
Band = Literal["high_risk", "caution", "no_known_signals"]
EntityType = Literal["upi", "phone", "domain", "url", "group_link", "wallet", "app"]
RingVia = Literal["same_upi", "same_phone", "same_domain", "same_group_link", "same_wallet", "same_script"]
EventName = Literal[
    "visit", "check_started", "check_done", "share_clicked", "ref_visit",
    "report", "quiz_done", "quiz_shared", "return_visit", "pricing_view",
    "checkout_started", "checkout_paid",  # server-only; db.record_event drops client copies
]
PlanId = Literal["family", "api"]
OrderStatus = Literal["pending", "paid", "failed"]
QuizAnswer = Literal["scam", "genuine"]

AnonId = Annotated[str, StringConstraints(pattern=r"^u_[A-Za-z0-9_-]{1,40}$")]
CheckId = Annotated[str, StringConstraints(pattern=r"^chk_[A-Za-z0-9_-]{1,40}$")]
QuizId = Annotated[str, StringConstraints(pattern=r"^q_[a-z]+_v[0-9]+$")]
OrderId = Annotated[str, StringConstraints(pattern=r"^ord_[A-Za-z0-9_-]{1,40}$")]
HttpsUrl = Annotated[str, StringConstraints(pattern=r"^https://", max_length=2000)]  # never javascript: in an href
HttpUrl = Annotated[str, StringConstraints(pattern=r"^https?://", max_length=2000)]
ShortKey = Annotated[str, StringConstraints(min_length=1, max_length=40)]
PropValue = Annotated[str, StringConstraints(max_length=200)] | int | float | bool | None


# ---- POST /api/check -------------------------------------------------------

class CheckInput(BaseModel):
    text: str | None = None
    image_b64: str | None = None
    image_mime: str | None = None
    audio_b64: str | None = None
    audio_mime: str | None = None


class CheckRequest(BaseModel):
    lang: Lang
    anon_id: AnonId
    ref: AnonId | None = None
    input: CheckInput


class Evidence(BaseModel):
    kind: Literal["quote", "lookup"]
    text: str
    source_url: HttpsUrl | None = None


class Signal(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^S[1-9]$")]
    label: str
    points: int
    evidence: Evidence


class Entity(BaseModel):
    type: EntityType
    masked: str


class Ring(BaseModel):
    linked_checks: int = Field(ge=0)
    linked_reports: int = Field(ge=0)
    via: list[RingVia]


class NextStep(BaseModel):
    text: str
    url: HttpsUrl | None = None


class Share(BaseModel):
    url: HttpUrl
    card_title: str


class CheckView(BaseModel):
    """GET /api/check/{check_id}: the public, masked view. Same as CheckResponse without `transcript`."""

    check_id: CheckId
    band: Band
    score: int = Field(ge=0, le=100)
    lang: Lang
    headline: str
    explanation: str
    signals: list[Signal]
    entities: list[Entity]
    ring: Ring
    next_steps: list[NextStep]
    share: Share
    unchecked: list[str]
    cached: bool
    latency_ms: int = Field(ge=0)


class CheckResponse(CheckView):
    transcript: str | None = None


# ---- POST /api/report ------------------------------------------------------

class ReportRequest(BaseModel):
    check_id: CheckId
    anon_id: AnonId
    consent_store_text: StrictBool  # consent must be an explicit true/false, never "yes" or 1
    note: Annotated[str, StringConstraints(max_length=500)] | None = None


class ReportResponse(BaseModel):
    report_id: str
    ok: bool


# ---- Quiz ------------------------------------------------------------------

class QuizItem(BaseModel):
    id: str
    text: str
    image_url: str | None = None


class QuizResponse(BaseModel):
    quiz_id: QuizId
    items: list[QuizItem]


class QuizAnswerRequest(BaseModel):
    quiz_id: QuizId
    anon_id: AnonId
    answers: Annotated[dict[ShortKey, QuizAnswer], Field(max_length=50)]


class QuizResult(BaseModel):
    id: str
    correct: bool
    answer: QuizAnswer
    why: str


class QuizAnswerResponse(BaseModel):
    score: int = Field(ge=0)
    total: int = Field(ge=0)
    results: list[QuizResult]
    share: Share


# ---- Events, stats, health -------------------------------------------------

class EventRequest(BaseModel):
    anon_id: AnonId
    event: EventName
    check_id: CheckId | None = None
    ref: AnonId | None = None
    props: Annotated[dict[ShortKey, PropValue], Field(max_length=20)] = Field(default_factory=dict)


class StatsResponse(BaseModel):
    users: int
    checks: int
    reports: int
    languages: dict[str, int]
    rings: int
    share_rate: float
    k_factor: float
    p50_ms: int
    p95_ms: int
    orders_paid: int
    updated_at: str


# ---- Payments (Dodo) -------------------------------------------------------

class Plan(BaseModel):
    id: PlanId
    name: str
    price_inr: int | float = Field(gt=0)
    interval: Literal["month"]
    available: bool


class PlansResponse(BaseModel):
    test_mode: bool
    plans: list[Plan]


class CheckoutRequest(BaseModel):
    plan: PlanId
    anon_id: AnonId


class CheckoutResponse(BaseModel):
    order_id: OrderId
    checkout_url: HttpsUrl


class OrderResponse(BaseModel):
    order_id: OrderId
    plan: PlanId
    status: OrderStatus


class HealthResponse(BaseModel):
    ok: bool
    llm: Literal["up", "down"]
    db: Literal["up", "down"]
