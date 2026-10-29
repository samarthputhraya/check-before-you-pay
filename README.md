# Check Before You Pay

Forward any investment tip or payment request and see the red flags in 5 seconds, in your own language.

> **Status: skeleton.** Every endpoint in [`API_CONTRACT.md`](API_CONTRACT.md) works and returns the contract's example data, marked with an `X-Sample: true` header. The web app renders that sample verdict. Role B replaces the stubs with the real pipeline (see [`docs/BUILD_BRIEF.md`](docs/BUILD_BRIEF.md)). The judges' README is written from Thursday evening.

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements.txt
cp .env.example .env            # fill in the keys you have; the skeleton runs with none
uvicorn backend.app:app --reload
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

## Deploy on Render

Railway closed new sign-ups on 29 Oct, so the live site runs on Render from [`render.yaml`](render.yaml).

1. In Render, choose **New**, then **Blueprint**, and pick this repo. The Blueprint creates one Docker web service in Singapore, with a 1 GB disk at `/data`. The SQLite file lives there (`SQLITE_PATH=/data/app.db`, already set in the Dockerfile), so usage data survives restarts and deploys.
2. Render asks for `GEMINI_API_KEY` and `PUBLIC_BASE_URL`. It generates `IDENTIFIER_SALT` and `ADMIN_TOKEN` itself.
3. Each push to `main` redeploys. A deploy goes live only after `/api/health` returns 200.

The disk needs a paid instance (about $7 a month plus $0.25 per GB). Keep exactly one instance: SQLite on a disk can't be shared between replicas. `railway.json` still works for anyone with an existing Railway account.

## Rules

Read [`AGENTS.md`](AGENTS.md) first. Secrets go only in `.env`, which is gitignored. Never change a shape in `API_CONTRACT.md` without role A.
