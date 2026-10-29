"""Tests for the review fixes: body limits without Content-Length, no user text in logs, masking on public pages,
URL and consent validation, text cleaning and cache headers."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import app as app_module
from backend import samples
from backend.privacy import mask_text
from backend.schemas import Evidence, NextStep, ReportRequest


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    from backend import db
    from backend.schemas import CheckResponse
    sample = CheckResponse.model_validate(samples._example('check_response'))
    db.save_check(tmp_path / 'test.db', sample, [], None, None, 'fixture',
                  'u_7f3a9c', 'text', 1.0, sample=True)
    return TestClient(app_module.app, raise_server_exceptions=False)


def chunks(total: int, size: int = 64 * 1024):
    sent = 0
    while sent < total:
        n = min(size, total - sent)
        sent += n
        yield b"x" * n


# ---- body limits ------------------------------------------------------------------------------------------------

def test_chunked_body_over_limit_is_rejected(client):
    # A generator body is sent with Transfer-Encoding: chunked and no Content-Length.
    resp = client.post("/api/check", content=chunks(9 * 1024 * 1024), headers={"content-type": "application/json"})
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "input_too_large"


def test_small_endpoints_have_a_small_limit(client):
    resp = client.post("/api/events", content=chunks(200 * 1024), headers={"content-type": "application/json"})
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "input_too_large"


def test_event_prop_values_are_capped(client):
    body = {"anon_id": "u_1", "event": "visit", "props": {"path": "x" * 201}}
    assert client.post("/api/events", json=body).status_code == 400
    body["props"] = {f"k{i}": 1 for i in range(21)}
    assert client.post("/api/events", json=body).status_code == 400


# ---- errors never log user content ------------------------------------------------------------------------------

def test_unhandled_error_returns_envelope_without_logging_content(client, monkeypatch, caplog):
    secret_text = "PRIVATE-MESSAGE-9876543210"

    async def boom(*args, **kwargs):
        raise RuntimeError(f"failed while handling {secret_text}")
    monkeypatch.setattr(app_module.pipeline, "run_check", boom)
    with caplog.at_level(logging.DEBUG):
        resp = client.post("/api/check", json={"lang": "en", "anon_id": "u_1", "input": {"text": secret_text}})
    assert resp.status_code == 500
    assert resp.json() == {"error": {"code": "internal_error",
                                     "message": "Something went wrong on our side. Please try again."}}
    assert secret_text not in caplog.text
    assert "9876543210" not in caplog.text


# ---- masking on public pages --------------------------------------------------------------------------------------

@pytest.mark.parametrize(("raw", "masked"), [
    ("Pay to tradepro.vip@ybl now", "Pay to tr…@ybl now"),
    ("Call +91 9876543210 today", "Call 98xxxxxx10 today"),
    ("Send USDT to TQ5NGy8Ke3b5JkEzVb9Ji8u2JAoPTxRQjF", "Send USDT to TQ5N…RQjF"),
    ("Already masked tr…@ybl stays", "Already masked tr…@ybl stays"),
])
def test_mask_text(raw, masked):
    assert mask_text(raw) == masked


def test_public_view_masks_identifiers_in_every_text_field(client, monkeypatch):
    real = samples._example("check_response")
    hostile = {**real, "explanation": "Pay tradepro.vip@ybl or call 9876543210",
               "signals": [{**real["signals"][0], "evidence": {"kind": "quote", "text": "send to abc.xyz@paytm",
                                                                "source_url": None}}]}
    from backend.schemas import CheckView
    monkeypatch.setattr(app_module.db, 'get_check', lambda *args: CheckView.model_validate(hostile))
    for path in ("/api/check/chk_A1", "/c/chk_A1"):
        body = client.get(path).text
        for raw in ("tradepro.vip@ybl", "9876543210", "abc.xyz@paytm"):
            assert raw not in body, (path, raw)


# ---- validation ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["javascript:alert(1)", "http://example.com", "data:text/html,x"])
def test_evidence_and_step_urls_must_be_https(url):
    with pytest.raises(ValidationError):
        Evidence(kind="lookup", text="x", source_url=url)
    with pytest.raises(ValidationError):
        NextStep(text="x", url=url)


@pytest.mark.parametrize("value", ["yes", 1, "true"])
def test_consent_must_be_a_real_boolean(value):
    with pytest.raises(ValidationError):
        ReportRequest(check_id="chk_A1", anon_id="u_1", consent_store_text=value)


def test_zero_width_only_text_is_empty(client):
    body = {"lang": "en", "anon_id": "u_1", "input": {"text": "​‌‍﻿ ⁠"}}
    resp = client.post("/api/check", json=body)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "empty_input"


def test_lone_surrogate_is_invalid(client):
    raw = b'{"lang":"en","anon_id":"u_1","input":{"text":"hi \\ud800 there"}}'
    resp = client.post("/api/check", content=raw, headers={"content-type": "application/json"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_request"


# ---- headers ------------------------------------------------------------------------------------------------------

def test_cache_headers(client):
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/app.js").headers["cache-control"] == "no-cache"
    assert "max-age" in client.get("/vendor/preact.module.js").headers["cache-control"]
    assert "cache-control" not in {k.lower() for k in client.get("/api/health").headers}


def test_share_page_loads_tracking_script(client):
    html = client.get("/c/chk_01JB8Q").text
    assert '<script type="module" src="/share.js"></script>' in html
    assert client.get("/share.js").status_code == 200
