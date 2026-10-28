"""Settings and hard limits. Values come from `.env` (never committed); see `.env.example`."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
EXAMPLES_DIR = ROOT / "examples"

load_dotenv(ROOT / ".env")

LANGS = ("en", "hi", "mr", "ta", "te", "kn", "bn", "hinglish")
IMAGE_MIMES = ("image/png", "image/jpeg")
AUDIO_MIMES = ("audio/ogg", "audio/mp4", "audio/mpeg")

MAX_TEXT_CHARS = 5_000
MAX_FILE_BYTES = 5 * 1024 * 1024
# A 5 MB file is about 6.7 MB as base64, plus the rest of the JSON body.
MAX_BODY_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    gemini_configured: bool
    public_base_url: str | None


def get_settings() -> Settings:
    raw_path = os.getenv("SQLITE_PATH", "./data/app.db")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    base = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or None
    return Settings(
        sqlite_path=path,
        gemini_configured=bool(os.getenv("GEMINI_API_KEY", "").strip()),
        public_base_url=base,
    )
