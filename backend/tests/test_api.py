"""Contract tests for the skeleton: every endpoint, every documented error code, and the examples themselves."""
from __future__ import annotations

import base64
import json
import io

from PIL import Image
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend.config import EXAMPLES_DIR, MAX_FILE_BYTES
from backend.schemas import (
    CheckoutRequest, CheckoutResponse, CheckRequest, CheckResponse, CheckView, EventRequest, HealthResponse,
    OrderResponse, PlansResponse, QuizAnswerRequest, QuizAnswerResponse, QuizResponse, ReportRequest, ReportResponse,
    StatsResponse,
)

def image_bytes(format):
    stream = io.BytesIO()
    Image.new('RGB', (2, 2), 'white').save(stream, format=format)
    return stream.getvalue()


PNG = image_bytes('PNG')
JPEG = image_bytes('JPEG')
OGG = (Path(__file__).parent / 'fixtures/voice.ogg').read_bytes()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    # Public-page tests use a persisted, explicitly labelled fixture.
    from backend import db
    sample = CheckResponse.model_validate(example('check_response'))
    sample.headline += ' (sample)'
    db.save_check(tmp_path / 'test.db', sample, [], None, None, 'fixture',
                  'u_7f3a9c', 'text', 1.0, sample=True)
    return TestClient(app_module.app)


def check_body(**input_fields) -> dict:
    fields = {"text": None, "image_b64": None, "image_mime": None, "audio_b64": None, "audio_mime": None}
    fields.update(input_fields)
    return {"lang": "en", "anon_id": "u_7f3a9c", "ref": None, "input": fields}


def assert_error(resp, status: int, code: str) -> None:
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]


# ---- examples are valid against the models ---------------------------------

@pytest.mark.parametrize(("name", "model"), [
    ("check_request", CheckRequest), ("check_response", CheckResponse), ("report_request", ReportRequest),
    ("report_response", ReportResponse), ("quiz_response", QuizResponse),
    ("quiz_answer_request", QuizAnswerRequest), ("quiz_answer_response", QuizAnswerResponse),
    ("event_request", EventRequest), ("stats_response", StatsResponse), ("health_response", HealthResponse),
    ("plans_response", PlansResponse), ("checkout_request", CheckoutRequest), ("checkout_response", CheckoutResponse),
    ("order_response", OrderResponse),
])
def test_example_matches_model(name, model):
    model.model_validate(example(name))


def test_example_score_is_sum_of_signal_points():
    resp = example("check_response")
    assert resp["score"] == sum(s["points"] for s in resp["signals"])


# ---- health -------------------------------------------------------------------

def test_health_reports_db_up_and_llm_down_without_key(client):
    resp = client.get("/api/health")
    assert resp.status_code == 503
    assert resp.json() == {"ok": False, "llm": "down", "db": "up"}


def test_health_reports_llm_up_with_ready_provider(client, monkeypatch):
    monkeypatch.setattr(app_module.llm.providers, "ready", True)
    assert client.get("/api/health").json()["llm"] == "up"


def test_health_is_503_when_db_unusable(client, monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("SQLITE_PATH", str(blocker / "sub" / "app.db"))
    resp = client.get("/api/health")
    assert resp.status_code == 503
    assert resp.json() == {"ok": False, "llm": "down", "db": "down"}


@pytest.mark.parametrize("path", ["/api/health", "/c/chk_01JB8Q"])
def test_head_is_supported(client, path):
    assert client.head(path).status_code == (503 if path == "/api/health" else 200)


# ---- POST /api/check ----------------------------------------------------------

def test_check_example_request(client):
    resp = client.post("/api/check", json=example("check_request"))
    assert resp.status_code == 200, resp.text
    assert "X-Sample" not in resp.headers
    body = CheckResponse.model_validate(resp.json())
    assert body.lang == "hi"
    assert body.check_id.startswith("chk_")
    assert body.share.url == f"http://testserver/c/{body.check_id}?ref=u_7f3a9c"
    assert "transcript" in resp.json()


def test_check_ids_are_unique(client):
    ids = {client.post("/api/check", json=check_body(text="hello")).json()["check_id"] for _ in range(5)}
    assert len(ids) == 5


def test_check_uses_public_base_url(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.app/")
    body = client.post("/api/check", json=check_body(text="hi")).json()
    assert body["share"]["url"].startswith("https://example.app/c/")


@pytest.mark.parametrize("text", [None, "", "   \n\t "])
def test_check_empty_input(client, text):
    assert_error(client.post("/api/check", json=check_body(text=text)), 400, "empty_input")


def test_check_text_at_limit_ok_and_over_limit_413(client):
    assert client.post("/api/check", json=check_body(text="a" * 5000)).status_code == 200
    assert_error(client.post("/api/check", json=check_body(text="a" * 5001)), 413, "input_too_large")


@pytest.mark.parametrize(("data", "mime"), [(PNG, "image/png"), (JPEG, "image/jpeg")])
def test_check_image_ok(client, data, mime):
    assert client.post("/api/check", json=check_body(image_b64=b64(data), image_mime=mime)).status_code == 200


def test_check_image_data_url_prefix_ok(client):
    resp = client.post("/api/check", json=check_body(image_b64="data:image/png;base64," + b64(PNG), image_mime="image/png"))
    assert resp.status_code == 200


@pytest.mark.parametrize("mime", [None, "image/gif", "image/webp"])
def test_check_image_unsupported_mime(client, mime):
    assert_error(client.post("/api/check", json=check_body(image_b64=b64(PNG), image_mime=mime)), 415, "unsupported_media")


def test_check_image_bytes_must_match_mime(client):
    assert_error(client.post("/api/check", json=check_body(image_b64=b64(PNG), image_mime="image/jpeg")),
                 415, "unsupported_media")


def test_check_image_bad_base64(client):
    assert_error(client.post("/api/check", json=check_body(image_b64="not base64!!", image_mime="image/png")),
                 400, "invalid_request")


def test_check_image_over_5mb(client):
    big = PNG + b"\x00" * (MAX_FILE_BYTES + 10 - len(PNG))
    assert_error(client.post("/api/check", json=check_body(image_b64=b64(big), image_mime="image/png")),
                 413, "input_too_large")


def test_check_image_exactly_5mb_ok(client):
    exact = PNG + b"\x00" * (MAX_FILE_BYTES - len(PNG))
    assert client.post("/api/check", json=check_body(image_b64=b64(exact), image_mime="image/png")).status_code == 200


def test_body_over_limit_rejected_before_parsing(client):
    resp = client.post("/api/check", content=b"x" * (8 * 1024 * 1024 + 1), headers={"content-type": "application/json"})
    assert_error(resp, 413, "input_too_large")


def test_check_audio_ok(client):
    assert client.post("/api/check", json=check_body(audio_b64=b64(OGG), audio_mime="audio/ogg")).status_code == 200


@pytest.mark.parametrize(("data", "mime"), [(OGG, "audio/wav"), (PNG, "audio/ogg"), (OGG, None)])
def test_check_audio_unsupported(client, data, mime):
    assert_error(client.post("/api/check", json=check_body(audio_b64=b64(data), audio_mime=mime)), 415, "unsupported_media")


@pytest.mark.parametrize("patch", [{"lang": "fr"}, {"anon_id": "user1"}, {"ref": "x"}, {"input": "text"}])
def test_check_invalid_fields(client, patch):
    body = check_body(text="hi")
    body.update(patch)
    assert_error(client.post("/api/check", json=body), 400, "invalid_request")


def test_check_rejects_non_json(client):
    resp = client.post("/api/check", content=b"{not json", headers={"content-type": "application/json"})
    assert_error(resp, 400, "invalid_request")


# ---- GET /api/check/{id} and /c/{id} ------------------------------------------

def test_check_view_has_no_transcript(client):
    resp = client.get("/api/check/chk_01JB8Q")
    assert resp.status_code == 200
    assert "transcript" not in resp.json()
    CheckView.model_validate(resp.json())


@pytest.mark.parametrize("bad", ["abc", "chk_", "chk_a$b", "rep_01JB8Q"])
def test_check_view_bad_id(client, bad):
    assert_error(client.get(f"/api/check/{bad}"), 404, "not_found")


def test_share_page_has_open_graph_tags(client):
    resp = client.get("/c/chk_01JB8Q")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    html = resp.text
    assert '<meta property="og:title" content="Check Before You Pay: High risk">' in html
    assert '<meta property="og:url" content="http://testserver/c/chk_01JB8Q">' in html
    assert "og:description" in html
    # WhatsApp shows a picture preview; the image for the band must actually be served.
    assert '<meta property="og:image" content="http://testserver/og/high_risk.png">' in html
    image = client.get("/og/high_risk.png")
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"


def test_share_page_escapes_everything(client, monkeypatch):
    from backend import samples
    real = samples.sample_view

    def hostile(*args, **kw):
        view = real(base="http://testserver", check_id="chk_01JB8Q")
        return view.model_copy(update={"headline": "<script>alert(1)</script>",
                                       "explanation": '"><img src=x onerror=alert(1)>'})
    monkeypatch.setattr(app_module.db, "get_check", hostile)
    html = client.get("/c/chk_01JB8Q").text
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html


def test_share_page_passes_ref_to_call_to_action(client):
    # The sample check is in Hindi: the visitor lands on the check page in Hindi, and the sharer is credited.
    assert 'href="/?lang=hi&amp;ref=u_12ab44"' in client.get("/c/chk_01JB8Q?ref=u_12ab44").text


@pytest.mark.parametrize("bad_ref", ['"><script>x</script>', "user1", "u_" + "a" * 60])
def test_share_page_drops_invalid_ref(client, bad_ref):
    resp = client.get("/c/chk_01JB8Q", params={"ref": bad_ref})
    assert resp.status_code == 200
    assert 'href="/?lang=hi"' in resp.text  # no ref at all, not a broken one
    assert "<script>x" not in resp.text


@pytest.mark.parametrize("path", ["/c/not-a-check", "/c/chk_doesnotexist"])
def test_share_page_missing_check_is_a_friendly_page(client, path):
    # People open these links from WhatsApp, so a missing check is a page with a way forward, not a JSON error.
    resp = client.get(path)
    assert resp.status_code == 404 and resp.headers["content-type"].startswith("text/html")
    assert 'href="/"' in resp.text and "noindex" in resp.text


# ---- report, quiz, events, stats ---------------------------------------------

def test_report(client):
    resp = client.post("/api/report", json=example("report_request"))
    assert resp.status_code == 200
    body = ReportResponse.model_validate(resp.json())
    assert body.ok and body.report_id.startswith("rep_")


def test_report_requires_consent_flag(client):
    body = example("report_request")
    del body["consent_store_text"]
    assert_error(client.post("/api/report", json=body), 400, "invalid_request")


def test_quiz_default_and_lang(client):
    assert client.get("/api/quiz").json()["quiz_id"] == "q_en_v1"
    resp = client.get("/api/quiz?lang=hi")
    assert resp.status_code == 200
    QuizResponse.model_validate(resp.json())
    assert resp.json()["quiz_id"] == "q_hi_v1"


def test_quiz_bad_lang(client):
    assert_error(client.get("/api/quiz?lang=xx"), 400, "invalid_request")


def test_quiz_answer(client):
    resp = client.post("/api/quiz/answer", json=example("quiz_answer_request"))
    assert resp.status_code == 200
    body = QuizAnswerResponse.model_validate(resp.json())
    assert body.share.url == "http://testserver/quiz?ref=u_7f3a9c"


def test_quiz_answer_bad_value(client):
    body = example("quiz_answer_request")
    body["answers"]["q1"] = "maybe"
    assert_error(client.post("/api/quiz/answer", json=body), 400, "invalid_request")


def test_events(client):
    resp = client.post("/api/events", json=example("event_request"))
    assert resp.status_code == 204
    assert resp.content == b""


def test_events_unknown_name(client):
    body = example("event_request") | {"event": "clicked_everything"}
    assert_error(client.post("/api/events", json=body), 400, "invalid_request")


def test_stats(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    StatsResponse.model_validate(resp.json())


# ---- routing and headers ------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/nope", "/api/check/x/y"])
def test_unknown_api_path_is_json_404(client, path):
    assert_error(client.get(path), 404, "not_found")


def test_wrong_method(client):
    assert_error(client.get("/api/report"), 404, "not_found")


@pytest.mark.parametrize("path", ["/", "/quiz", "/pricing", "/stats"])
def test_web_routes_serve_the_app(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert '<div id="app">' in resp.text


def test_security_headers(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_security_headers_on_pages_and_api(client):
    for path in ("/", "/api/health"):
        headers = client.get(path).headers
        assert "frame-ancestors 'none'" in headers["content-security-policy"]
        assert "script-src 'self' 'sha256-" in headers["content-security-policy"]  # the import map's hash was found
        assert headers["x-frame-options"] == "DENY"


def test_share_page_speaks_the_checks_language(client):
    html = client.get("/c/chk_01JB8Q").text  # the sample check is in Hindi
    assert 'lang="hi"' in html and "ख़तरे के संकेत" in html and "अब क्या करें" in html
    assert '<meta property="og:title" content="Check Before You Pay: High risk">' in html  # preview stays English
    # The verdict can be heard; the MP3 is made only when someone presses play.
    assert 'यह नतीजा सुनें' in html and 'preload="none"' in html and 'src="/api/check/chk_01JB8Q/audio"' in html
