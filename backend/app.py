"""Check Before You Pay: the FastAPI app. Serves the JSON API (see API_CONTRACT.md) and the web app in web/.

Run locally:  uvicorn backend.app:app --reload
"""
from __future__ import annotations

import logging
import asyncio
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager, suppress

from fastapi import BackgroundTasks, FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError

from backend import db, llm, pipeline, rate_limit, webhooks
from backend.cache import consent_buffer
from backend.config import WEB_DIR, get_settings
from backend.errors import ApiError, install_error_handlers
from backend.guard import Guard
from backend.inputs import validate_check_input
from backend.privacy import public_view
from backend.samples import sample_quiz, sample_quiz_answer
from backend.schemas import (
    AnonId, CheckId, CheckRequest, CheckResponse, CheckView, EventRequest, HealthResponse, Lang,
    QuizAnswerRequest, QuizAnswerResponse, QuizResponse, ReportRequest, ReportResponse, StatsResponse,
)
from backend.share_page import render_share_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # it logs full outgoing URLs, and webhook URLs carry secrets
logging.getLogger("httpx2").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(db.ping, get_settings().sqlite_path)
    await llm.providers.initialize()
    webhook_worker = asyncio.create_task(webhooks.worker())
    try:
        yield
    finally:
        webhook_worker.cancel()
        with suppress(asyncio.CancelledError):
            await webhook_worker
        await llm.providers.close()


app = FastAPI(title="Check Before You Pay", version="0.2.0", docs_url="/api/docs", redoc_url=None, lifespan=lifespan,
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
    return HealthResponse(ok=db_up, llm="up" if llm.providers.ready else "down", db="up" if db_up else "down")


@app.post("/api/check", response_model=CheckResponse)
async def check(body: CheckRequest, request: Request, response: Response) -> CheckResponse:
    inp = await asyncio.to_thread(validate_check_input, body.input)
    await asyncio.to_thread(rate_limit.enforce, body.anon_id, request.client.host if request.client else 'unknown')
    response.headers['Cache-Control'] = 'no-store'
    return await pipeline.run_check(body, inp, base_url(request))


@app.get("/api/check/{check_id}", response_model=CheckView)
def check_view(check_id: str, request: Request, response: Response) -> CheckView:
    _require_check_id(check_id)
    view = db.get_check(get_settings().sqlite_path, check_id)
    if view is None:
        raise ApiError(404, 'not_found', 'No check with that ID.')
    return public_view(view)


@app.post("/api/report", response_model=ReportResponse)
def report(body: ReportRequest, response: Response, background_tasks: BackgroundTasks) -> ReportResponse:
    text = consent_buffer.peek(body.check_id, body.anon_id, body.consent_store_text)
    configured = bool(os.getenv('VIASOCKET_REPORT_WEBHOOK_URL', '').strip())
    try:
        report_id, created = db.add_report(get_settings().sqlite_path, body.check_id, body.anon_id, text,
                                     body.note if body.consent_store_text else None, webhook_enabled=configured)
    except KeyError:
        raise ApiError(404, 'not_found', 'No check with that ID.') from None
    except (sqlite3.Error, OSError):
        raise ApiError(503, 'internal_error', 'We could not save your report. Please try again.') from None
    consent_buffer.take(body.check_id, body.anon_id, False)
    if created and configured:
        background_tasks.add_task(webhooks.deliver_pending)
    elif created:
        logging.getLogger('cbyp').info('viasocket not configured')
    return ReportResponse(report_id=report_id, ok=True)


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
    db.record_event(get_settings().sqlite_path, body)
    return Response(status_code=204)


@app.get("/api/stats", response_model=StatsResponse)
def stats(response: Response) -> StatsResponse:
    return db.stats(get_settings().sqlite_path)


@app.get('/api/admin/export', include_in_schema=False)
def export_database(request: Request) -> Response:
    token = os.getenv('ADMIN_TOKEN', '')
    provided = request.headers.get('authorization', '').removeprefix('Bearer ')
    if not token or not secrets.compare_digest(token, provided):
        raise ApiError(404, 'not_found', 'Not found.')
    return Response(db.export_database(get_settings().sqlite_path), media_type='application/vnd.sqlite3',
                    headers={'Content-Disposition':'attachment; filename="check-before-you-pay.db"', 'Cache-Control':'no-store'})


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
    view = db.get_check(get_settings().sqlite_path, check_id)
    if view is None:
        raise ApiError(404, 'not_found', 'No check with that ID.')
    view = public_view(view)
    page_url = f"{base_url(request)}/c/{check_id}"
    return HTMLResponse(render_share_page(view, page_url, ref))


@app.get("/quiz", include_in_schema=False)
@app.get("/pricing", include_in_schema=False)
@app.get("/stats", include_in_schema=False)
def spa_routes() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
