"""Check Before You Pay: the FastAPI app. Serves the JSON API (see API_CONTRACT.md) and the web app in web/.

Run locally:  uvicorn backend.app:app --reload
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError

from backend import db
from backend.config import WEB_DIR, get_settings
from backend.errors import ApiError, install_error_handlers
from backend.guard import Guard
from backend.ids import new_id
from backend.inputs import validate_check_input
from backend.samples import sample_check, sample_quiz, sample_quiz_answer, sample_stats, sample_view
from backend.schemas import (
    AnonId, CheckId, CheckRequest, CheckResponse, CheckView, EventRequest, HealthResponse, Lang,
    QuizAnswerRequest, QuizAnswerResponse, QuizResponse, ReportRequest, ReportResponse, StatsResponse,
)
from backend.share_page import render_share_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # it logs full outgoing URLs, and webhook URLs carry secrets

app = FastAPI(title="Check Before You Pay", version="0.1.0", docs_url="/api/docs", redoc_url=None,
              openapi_url="/api/openapi.json")
install_error_handlers(app)
app.add_middleware(Guard)

SAMPLE_HEADER = {"X-Sample": "true"}  # stub responses; removed as each endpoint becomes real


def base_url(request: Request) -> str:
    return get_settings().public_base_url or str(request.base_url).rstrip("/")


# ---- API --------------------------------------------------------------------

@app.api_route("/api/health", methods=["GET", "HEAD"], response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    s = get_settings()
    db_up = db.ping(s.sqlite_path)
    # 503 when the database can't be written, so a deploy with a missing or read-only volume fails its healthcheck
    # instead of going live without storing any usage data. Checks themselves still work while the db is down.
    if not db_up:
        response.status_code = 503
    # Skeleton: "up" means a Gemini key is configured. Role B makes this a real model check.
    return HealthResponse(ok=db_up, llm="up" if s.gemini_configured else "down", db="up" if db_up else "down")


@app.post("/api/check", response_model=CheckResponse)
def check(body: CheckRequest, request: Request, response: Response) -> CheckResponse:
    t0 = time.perf_counter()
    validate_check_input(body.input)
    response.headers.update(SAMPLE_HEADER)
    return sample_check(check_id=new_id("chk"), lang=body.lang, base=base_url(request),
                        anon_id=body.anon_id, latency_ms=int((time.perf_counter() - t0) * 1000))


@app.get("/api/check/{check_id}", response_model=CheckView)
def check_view(check_id: str, request: Request, response: Response) -> CheckView:
    _require_check_id(check_id)
    response.headers.update(SAMPLE_HEADER)
    return sample_view(check_id=check_id, base=base_url(request))


@app.post("/api/report", response_model=ReportResponse)
def report(body: ReportRequest, response: Response) -> ReportResponse:
    response.headers.update(SAMPLE_HEADER)
    return ReportResponse(report_id=new_id("rep"), ok=True)


@app.get("/api/quiz", response_model=QuizResponse)
def quiz(response: Response, lang: Lang = Query("en")) -> QuizResponse:
    response.headers.update(SAMPLE_HEADER)
    return sample_quiz(lang)


@app.post("/api/quiz/answer", response_model=QuizAnswerResponse)
def quiz_answer(body: QuizAnswerRequest, request: Request, response: Response) -> QuizAnswerResponse:
    response.headers.update(SAMPLE_HEADER)
    return sample_quiz_answer(base=base_url(request), anon_id=body.anon_id)


@app.post("/api/events", status_code=204)
def events(body: EventRequest) -> Response:
    return Response(status_code=204, headers=SAMPLE_HEADER)


@app.get("/api/stats", response_model=StatsResponse)
def stats(response: Response) -> StatsResponse:
    response.headers.update(SAMPLE_HEADER)
    return sample_stats()


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(path: str) -> Response:
    raise ApiError(404, "not_found", "Not found.")


# ---- Pages ------------------------------------------------------------------

_CHECK_ID = TypeAdapter(CheckId)


def _require_check_id(check_id: str) -> None:
    try:
        _CHECK_ID.validate_python(check_id)
    except ValidationError:
        raise ApiError(404, "not_found", "No check with that ID.") from None


_ANON_ID = TypeAdapter(AnonId)


@app.api_route("/c/{check_id}", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
def share_page(check_id: str, request: Request, ref: str | None = None) -> HTMLResponse:
    _require_check_id(check_id)
    try:
        ref = _ANON_ID.validate_python(ref) if ref else None
    except ValidationError:
        ref = None  # a mangled ref must not break the page; we just don't credit anyone
    view = sample_view(check_id=check_id, base=base_url(request))
    page_url = f"{base_url(request)}/c/{check_id}"
    return HTMLResponse(render_share_page(view, page_url, ref), headers=SAMPLE_HEADER)


@app.get("/quiz", include_in_schema=False)
@app.get("/pricing", include_in_schema=False)
@app.get("/stats", include_in_schema=False)
def spa_routes() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
