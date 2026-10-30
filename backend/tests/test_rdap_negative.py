import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import lookups
from backend.app import app
from backend.language import UNREGISTERED


@pytest.mark.parametrize('http_status, expected', [(404, (-1, 'https://rdap.verisign.com/com/v1/domain/example.com')),
                                                 (429, None), (500, None)])
def test_authoritative_rdap_negative_distinct_from_failure(monkeypatch, http_status, expected):
    lookups._ages.clear()
    original = httpx.AsyncClient
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(http_status, json={'errorCode': http_status})
    monkeypatch.setattr(lookups.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    first = asyncio.run(lookups.domain_age('example.com'))
    assert first == expected
    if http_status == 404:
        assert asyncio.run(lookups.domain_age('example.com')) == first
        assert len(requests) == 1
    lookups._ages.clear()


@pytest.mark.parametrize('lang', list(UNREGISTERED))
def test_zero_point_registered_evidence_all_languages(tmp_path, monkeypatch, lang):
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setattr(lookups, 'domain_ages', AsyncMock(return_value=(
        {'missing-site.com': (-1, 'https://rdap.verisign.com/com/v1/domain/missing-site.com')}, False)))
    result = TestClient(app).post('/api/check', json={
        'lang': lang, 'anon_id': 'u_testnegative', 'input': {'text': 'https://missing-site.com'}})
    assert result.status_code == 200
    body = result.json()
    assert 'domain_age' not in body['unchecked']
    assert body['score'] == 0
    evidence = next(s for s in body['signals'] if s['id'] == 'S3')
    assert evidence['points'] == 0
    assert evidence['label'] == UNREGISTERED[lang]
    assert evidence['evidence']['text'] == 'missing-site.com'  # no 'RDAP 404' jargon; the Source link carries it
    assert evidence['evidence']['source_url'].startswith('https://rdap.')
