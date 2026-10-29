# Check Before You Pay

Forward any investment tip or payment request and see the red flags in 5 seconds, in your own language.

> **Status: skeleton.** Every endpoint in [`API_CONTRACT.md`](API_CONTRACT.md) works and returns the contract's example data, marked with an `X-Sample: true` header. The web app renders that sample verdict. Role B replaces the stubs with the real pipeline (see [`docs/BUILD_BRIEF.md`](docs/BUILD_BRIEF.md)). The judges' README is written from Thursday evening.

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements.txt
cp .env.example .env            # fill in the keys you have; the skeleton runs with none
uvicorn backend.app:app --reload --no-proxy-headers
```

Open http://localhost:8000. The API docs are at http://localhost:8000/api/docs.

Run the tests with `pytest`.

## Repo map

| Path | What it is |
|---|---|
| `backend/app.py` | FastAPI routes: the JSON API, the share page `/c/{id}`, and the web app |
| `backend/schemas.py` | Request and response models; they mirror `API_CONTRACT.md` |
| `backend/inputs.py` | Validates `/api/check` input: sizes, MIME types and file signatures |
| `backend/errors.py` | The one error shape: `{"error": {"code", "message"}}` |
| `backend/samples.py` | Stub responses from `examples/`. Replaced endpoint by endpoint |
| `backend/share_page.py` | Server-rendered share page with Open Graph tags for WhatsApp previews |
| `backend/db.py` | SQLite connection (WAL). Role B adds the link tables here |
| `web/` | Preact + htm as ES modules, no build step. Preact and htm are vendored in `web/vendor/` |
| `examples/` | One example JSON per endpoint. Tests check each one against the models |
| `seed/` | Demo data, loaded with one command (role B) |

## Deploy on Railway

1. Install the CLI (`npm i -g @railway/cli`), then run `railway login` and `railway init` in this folder.
2. Add a **volume** to the service, mounted at `/data`. The SQLite file lives there (`SQLITE_PATH=/data/app.db`, already set in the Dockerfile), so usage data survives restarts.
3. Set the variables from `.env.example` in the Railway dashboard. Set `PUBLIC_BASE_URL` to the public URL so share links point at it.
4. Run `railway up`. Railway builds the `Dockerfile` and checks `/api/health` (see `railway.json`).

Keep exactly one instance: SQLite on a volume can't be shared between replicas.

## Rules

Read [`AGENTS.md`](AGENTS.md) first. Secrets go only in `.env`, which is gitignored. Never change a shape in `API_CONTRACT.md` without role A.

## Backend status (role B, 29 October)

The check, public verdict, reports, events and stats now use the real backend.
The quiz still returns labelled sample responses. API shapes are unchanged.

- Gemini extracts source-verified claims and explains fixed scores; it never
  chooses points. Model names are discovered from the configured key. Run
  `python -m backend.model_inventory` to inspect available names. Optional OpenAI
  fallback models must be explicitly configured and accessible to that key.
- Deterministic S1–S7 checks, domain lookalikes, RDAP age lookups, hashed entity
  links, model-specific script embeddings, cache and persistent rate limits run
  behind `/api/check`. Failed checks score zero and appear in `unchecked`.
- PNG/JPEG and OGG/M4A/MP3 are validated before processing. Text extraction falls
  back to regex when the provider fails. Unreadable media returns a plain error.
- SQLite stores masked verdicts and HMAC identifiers. Source text stays in a
  bounded 15-minute memory buffer and is persisted only with Report consent from
  the submitting anonymous ID. A restart clears that buffer.
- Set a random `IDENTIFIER_SALT` of at least 32 characters before testing links.
  Without it, checks still return verdicts with links marked unchecked.
- Configure `VIASOCKET_REPORT_WEBHOOK_URL` for the durable report delivery worker.
  It sends masked metadata, retries up to three times, and never sends source text.
  Empty URLs skip delivery and log `viasocket not configured`. Delivery starts
  after the report response. See [the exact payload and setup](docs/VIASOCKET.md).
  The family-alert and sheet workflow must still be configured in viaSocket.
- `GET /api/admin/export` downloads an online SQLite backup when supplied
  `Authorization: Bearer <ADMIN_TOKEN>`. Keep the token in `.env`.

Run `python -m seed.load` for explicitly labelled synthetic ring examples;
see [seed setup](seed/README.md) for optional phishing-feed configuration.
Run `python -m pytest` for offline contract, privacy, scoring and outage tests.
Tests replace provider calls and never spend credits or send webhooks.

Latest real-key benchmark: text p50/p95 2.56/3.43 seconds (20/20 complete);
screenshots 4.16/4.76 seconds (10/10 complete). Voice returned 9/10 responses,
with 8/10 completing every risk check, and still needs reliability and phone
acceptance work. These are local measurements, not deployment latency or usage
metrics. All 306 offline tests pass. See the
[review resolutions and benchmark](docs/REVIEW_FIXES.md) for every review finding,
retry/health behavior, event validation and Railway IP settings.
See [the role B handoff](docs/BACKEND_HANDOFF.md) for file ownership,
team setup and the remaining external steps. Phone/Railway validation, consented
real seed collection and the external viaSocket workflow remain outstanding.
