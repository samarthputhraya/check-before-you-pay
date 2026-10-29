"""Offline provider boundary: tests never use credentials from the developer's .env."""
from __future__ import annotations

import pytest

from backend import llm, lookups
from backend.extraction import Claim, Extraction, verified_extraction
from backend.links import Embedding


@pytest.fixture(autouse=True)
def offline_providers(monkeypatch):
    for name in ('GEMINI_API_KEY', 'OPENAI_API_KEY', 'VIASOCKET_REPORT_WEBHOOK_URL',
                 'PHISHTANK_FEED_PATH', 'ADMIN_TOKEN', 'GEMINI_EXTRACT_MODEL', 'GEMINI_EXPLAIN_MODEL',
                 'GEMINI_EMBED_MODEL', 'GEMINI_TTS_MODEL', 'OPENAI_MODEL', 'OPENAI_EMBED_MODEL',
                 'OPENAI_TRANSCRIBE_MODEL'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('IDENTIFIER_SALT', 'test-only-identifier-salt-32-characters')
    monkeypatch.setattr(llm.providers, 'ready', False)

    async def extract(text):
        claims = [Claim(type=kind, quote=quote) for kind, quote in (
            ('guaranteed_returns', '300% guaranteed'),
            ('vip_or_institutional_account', 'institutional account')) if quote in text]
        return verified_extraction(Extraction(claims=claims), text)

    async def embed(text):
        return Embedding('test:embedding', [1.0, 0.0, 0.0])

    async def explain(*args):
        return llm.Explanation(explanation='Review the evidence before paying.', signals=[])

    async def transcribe(*args):
        return 'Investment: pay sample@ybl for an institutional account. 300% guaranteed.'

    async def read_media(data, mime, text=''):
        transcript = await transcribe()
        return transcript, await extract(text + '\n' + transcript)

    async def ages(domains):
        return {}, False

    monkeypatch.setattr(llm, 'extract', extract)
    monkeypatch.setattr(llm, 'embed', embed)
    monkeypatch.setattr(llm, 'explain', explain)
    monkeypatch.setattr(llm, 'transcribe', transcribe)
    monkeypatch.setattr(llm, 'read_media', read_media)
    monkeypatch.setattr(lookups, 'domain_ages', ages)
    monkeypatch.setattr(lookups, 'phishing_hits', lambda urls: ([], False))
