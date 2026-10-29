"""Check Before You Pay: the FastAPI app. Serves the JSON API (see API_CONTRACT.md) and the web app in web/.

Run locally:  uvicorn backend.app:app --reload
"""
from __future__ import annotations

import logging
import asyncio
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager, suppress

from fastapi import BackgroundTasks, FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError

from backend import db, events as event_proof, llm, payments, pipeline, quiz as quizzes, rate_limit, webhooks
from backend.cache import consent_buffer
from backend.config import WEB_DIR, get_settings
from backend.errors import ApiError, install_error_handlers
from backend.guard import Guard
from backend.inputs import validate_check_input
from backend.privacy import public_view
from backend.schemas import (
    AnonId, CheckId, CheckoutRequest, CheckoutResponse, CheckRequest, CheckResponse, CheckView, EventRequest,
    HealthResponse, Lang, OrderId, OrderResponse, PlansResponse, QuizAnswerRequest, QuizAnswerResponse, QuizResponse,
    ReportRequest, ReportResponse, Share, StatsResponse,
)
from backend.share_page import render_share_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # it logs full outgoing URLs, and webhook URLs carry secrets
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").addFilter(payments.RedactReturnQuery())

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(db.prepare_cache, get_settings().sqlite_path)
    except (sqlite3.Error, OSError):
        pass  # Health reports the outage; checks retain their regex/zero-link fallback.
    try:
        quizzes.bank()  # read and validate the quiz files once, before the first player
    except (OSError, ValueError) as exc:  # our own seed content, so the message is fine to log
        logging.getLogger('cbyp').error('quiz content failed to load: %s', exc)  # checks still run
    await llm.providers.initialize()
    webhook_worker = asyncio.create_task(webhooks.worker())
    model_worker = asyncio.create_task(llm.providers.refresh_loop())
    try:
        yield
    finally:
        webhook_worker.cancel()
        model_worker.cancel()
        with suppress(asyncio.CancelledError):
            await webhook_worker
        with suppress(asyncio.CancelledError):
            await model_worker
        await llm.providers.close()


app = FastAPI(title="Check Before You Pay", version="0.2.0", docs_url="/api/docs", redoc_url=None, lifespan=lifespan,
              openapi_url="/api/openapi.json")
install_error_handlers(app)
app.add_middleware(Guard)


def base_url(request: Request) -> str:
    return get_settings().public_base_url or str(request.base_url).rstrip("/")


# ---- API --------------------------------------------------------------------

@app.api_route("/api/health", methods=["GET", "HEAD"], response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    s = get_settings()
    db_up = db.ping(s.sqlite_path)
    # 503 when the database can't be written, so a deploy with a missing or read-only volume fails its healthcheck
    # instead of going live without storing any usage data. Checks themselves still work while the db is down.
    if not db_up or not llm.providers.ready:
        response.status_code = 503
    return HealthResponse(ok=db_up and llm.providers.ready, llm="up" if llm.providers.ready else "down", db="up" if db_up else "down")


@app.post("/api/check", response_model=CheckResponse)
async def check(body: CheckRequest, request: Request, response: Response) -> CheckResponse:
    inp = await asyncio.to_thread(validate_check_input, body.input)
    await asyncio.to_thread(rate_limit.enforce, body.anon_id, rate_limit.client_ip(request))
    response.headers['Cache-Control'] = 'no-store'
    result = await pipeline.run_check(body, inp, base_url(request))
    event_proof.issue(response, body.anon_id, secure=base_url(request).startswith('https://'))
    return result


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
        report_id, created, text_saved = db.add_report(get_settings().sqlite_path, body.check_id, body.anon_id, text,
                                     body.note if body.consent_store_text else None, webhook_enabled=configured)
    except KeyError:
        raise ApiError(404, 'not_found', 'No check with that ID.') from None
    except (sqlite3.Error, OSError):
        raise ApiError(500, 'internal_error', 'We could not save your report. Please try again.') from None
    consent_buffer.take(body.check_id, body.anon_id, False)
    if created and configured:
        background_tasks.add_task(webhooks.deliver_pending)
    elif created:
        logging.getLogger('cbyp').info('viasocket not configured')
    return ReportResponse(report_id=report_id, ok=True, text_saved=text_saved)


@app.get("/api/quiz", response_model=QuizResponse)
def quiz(lang: Lang = Query("en")) -> QuizResponse:
    return quizzes.public(quizzes.for_lang(lang))


@app.post("/api/quiz/answer", response_model=QuizAnswerResponse)
def quiz_answer(body: QuizAnswerRequest, request: Request, response: Response) -> QuizAnswerResponse:
    quiz_set = quizzes.by_id(body.quiz_id)
    if quiz_set is None:
        raise ApiError(400, 'invalid_request', 'quiz_id: no quiz with that ID.')
    rate_limit.enforce_quiz(body.anon_id, rate_limit.client_ip(request))
    score, results = quizzes.score(quiz_set, body.answers)
    try:
        db.save_quiz_result(get_settings().sqlite_path, body.anon_id, quiz_set.quiz_id, quiz_set.lang, score)
    except (sqlite3.Error, OSError):
        # The player still gets their score. Without the row, a later quiz_shared simply isn't counted.
        logging.getLogger('cbyp').warning('quiz result not stored')
    base = base_url(request)
    response.headers['Cache-Control'] = 'no-store'
    event_proof.issue(response, body.anon_id, secure=base.startswith('https://'))  # lets quiz_shared count
    return QuizAnswerResponse(score=score, total=len(results), results=results,
                              share=Share(url=f'{base}/quiz?ref={body.anon_id}',
                                          card_title=quiz_set.title(score, len(results))))


@app.post("/api/events", status_code=204)
def events(body: EventRequest, request: Request) -> Response:
    rate_limit.enforce_events(body.anon_id, rate_limit.client_ip(request))
    if body.event in ('share_clicked', 'quiz_shared') and not event_proof.verified(request, body.anon_id):
        return Response(status_code=204)
    db.record_event(get_settings().sqlite_path, body)
    return Response(status_code=204)


_stats_cache: tuple[float, str, StatsResponse] | None = None


@app.get("/api/stats", response_model=StatsResponse)
def stats(response: Response) -> StatsResponse:
    # Every open /stats page polls this. Once the full count is slow (about 20,000 checks), serve it up to 15 s old;
    # while it's quick, every call stays exact.
    global _stats_cache
    path = str(get_settings().sqlite_path)
    if _stats_cache and _stats_cache[1] == path and time.monotonic() - _stats_cache[0] < 15:
        return _stats_cache[2]
    started = time.monotonic()
    result = db.stats(get_settings().sqlite_path, payments.config().mode)
    _stats_cache = (time.monotonic(), path, result) if time.monotonic() - started > 0.25 else None
    return result


@app.get("/api/plans", response_model=PlansResponse)
async def plans() -> PlansResponse:
    cfg = payments.config()
    return PlansResponse(test_mode=cfg.mode != 'live_mode', plans=await payments.plans(cfg))


@app.post("/api/checkout", response_model=CheckoutResponse)
async def checkout(body: CheckoutRequest, request: Request, response: Response) -> CheckoutResponse:
    await asyncio.to_thread(rate_limit.enforce_checkout, body.anon_id, rate_limit.client_ip(request))
    order_id, url = await payments.start_checkout(get_settings().sqlite_path, payments.config(), body.plan,
                                                  body.anon_id, base_url(request))
    response.headers['Cache-Control'] = 'no-store'
    return CheckoutResponse(order_id=order_id, checkout_url=url)


@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def order_status(order_id: str, response: Response) -> OrderResponse:
    try:
        _ORDER_ID.validate_python(order_id)
    except ValidationError:
        raise ApiError(404, 'not_found', 'No order with that ID.') from None
    order = db.get_order(get_settings().sqlite_path, order_id)
    if order is None:
        raise ApiError(404, 'not_found', 'No order with that ID.')
    response.headers['Cache-Control'] = 'no-store'  # polled until the webhook lands
    return OrderResponse(order_id=order['id'], plan=order['plan'], status=order['status'])


@app.post("/api/dodo/webhook", include_in_schema=False)
async def dodo_webhook(request: Request) -> Response:
    await payments.webhook(get_settings().sqlite_path, request.headers, await request.body())
    return Response(status_code=200)


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
_ORDER_ID = TypeAdapter(OrderId)


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
