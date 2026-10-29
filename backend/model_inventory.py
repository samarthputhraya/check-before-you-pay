"""Print accessible model names/capabilities, never keys. Run before choosing .env model names."""
from __future__ import annotations

import os

from google import genai
from google.genai import types

from backend.config import get_settings


def main() -> None:
    get_settings()
    if not os.getenv('GEMINI_API_KEY'):
        raise SystemExit('Set GEMINI_API_KEY in .env first.')
    try:
        with genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=types.HttpOptions(timeout=10000)) as client:
            for model in client.models.list():
                print(model.name, ', '.join(model.supported_actions or []))
    except Exception as exc:
        raise SystemExit('Model discovery failed: ' + type(exc).__name__) from None


if __name__ == '__main__':
    main()
