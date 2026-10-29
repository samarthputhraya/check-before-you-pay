"""Real check orchestration. The model extracts/explains; fixed signals determine every point."""
from __future__ import annotations

import asyncio
import re
import sqlite3
import time
from collections.abc import Awaitable
from typing import TypeVar

from backend import db, language, llm, lookups, weights
from backend.cache import consent_buffer, input_hash
from backend.config import get_settings
from backend.errors import ApiError
from backend.extraction import link_host, regex_extract, source_text
from backend.ids import new_id
from backend.inputs import ValidInput
from backend.links import display_entities, identifiers
from backend.privacy import mask_text, public_view
from backend.schemas import CheckRequest, CheckResponse, Ring, Share
from backend.signals import evaluate, score, signal

T = TypeVar('T')
DB_ERRORS = (sqlite3.Error, OSError, ValueError)
LINK_NAMES = {'same_upi': 'UPI ID', 'same_phone': 'phone number', 'same_domain': 'website',
              'same_group_link': 'group link', 'same_wallet': 'wallet'}


async def bounded(task: Awaitable[T], seconds: float) -> T | None:
    try:
        async with asyncio.timeout(max(0.001, seconds)):
            return await task
    except Exception:
        return None


async def run_check(body: CheckRequest, inp: ValidInput, base: str) -> CheckResponse:
    started = time.perf_counter()
    created = time.time()
    deadline = started + (9.5 if inp.image or inp.audio else 4.65)
    path = get_settings().sqlite_path
    key = input_hash(inp)
    check_id = new_id('chk')
    share_url = f'{base}/c/{check_id}?ref={body.anon_id}'
    unchecked: list[str] = []
    # Each submitted check has its own ID/owner for consent and usage, even on cache hits.
    try:
        cached = await asyncio.to_thread(db.cached_check, path, key, body.lang)
    except DB_ERRORS:
        cached = None
        unchecked.append('links')
    if cached:
        result = CheckResponse(**(cached.model_dump() | {'check_id':check_id, 'cached':True,
            'share':{'url':share_url, 'card_title':cached.share.card_title}, 'latency_ms':0, 'transcript':None}))
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            await asyncio.to_thread(db.save_check, path, result, [], None, None, key, body.anon_id,
                                    inp.input_type, created, body.ref)
        except DB_ERRORS:
            result.unchecked = sorted(set(result.unchecked + ['links']))
            result.signals = [s for s in result.signals if s.id not in ('S4','S5')]
            result.score, result.band = score(result.signals)
            result.ring = Ring(linked_checks=0, linked_reports=0, via=[])
            result.headline, result.explanation, result.next_steps = language.fallback(result.band, body.lang, result.unchecked)
        if inp.text:
            consent_buffer.put(check_id, body.anon_id, inp.text)
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        return result

    transcript = None
    text = inp.text or ''
    for data, mime in [(inp.image, inp.image_mime), (inp.audio, inp.audio_mime)]:
        if data:
            media_budget = 5.0 if mime and mime.startswith('audio/') else 3.5
            reading = await bounded(llm.transcribe(data, mime), min(media_budget, deadline - time.perf_counter() - 2))
            if reading and reading.strip():
                transcript = '\n'.join(filter(None, [transcript, reading]))
                text = '\n'.join(filter(None, [text, reading]))
            else:
                unchecked.extend(['transcription', 'claims'])
    if not text.strip():
        raise ApiError(503, 'check_unavailable', 'We could not read this file. Paste the message text or send a clearer file.')
    text = text[:20000]
    clean = source_text(text)
    regex = regex_extract(clean)
    # Independent evidence work runs concurrently, rather than adding its worst-case delays.
    has_script = len(clean.split()) >= 4
    extract_task = bounded(llm.extract(clean), min(2.8, deadline - time.perf_counter() - 1.2))
    embed_task = bounded(llm.embed(clean), 2.0) if has_script else asyncio.sleep(0, result=False)
    extracted, embedding, ages_result = await asyncio.gather(
        extract_task, embed_task, lookups.domain_ages([d for d in regex.entities.domains if link_host(d)]))
    if extracted is None:
        extracted = regex
        unchecked.append('claims')
    ages, age_failed = ages_result
    if age_failed:
        unchecked.append('domain_age')
    feed_result = await bounded(asyncio.to_thread(lookups.phishing_hits, extracted.entities.urls),
                                min(0.3, deadline - time.perf_counter() - 0.8))
    hits, feed_failed = feed_result if feed_result is not None else ([], True)
    if feed_failed:
        unchecked.append('phishing_feed')
    base_signals = evaluate(clean, extracted, ages, hits)
    ring = Ring(linked_checks=0, linked_reports=0, via=[])
    script_id = None
    script_count = 0
    records = []
    if has_script and embedding is None:
        unchecked.append('script_similarity')
    try:
        records = identifiers(extracted)
        if 'links' not in unchecked:
            context = await bounded(asyncio.to_thread(db.link_context, path, records,
                                                     embedding or None, created, key),
                                    min(2, deadline - time.perf_counter() - 0.8))
            if context is None:
                unchecked.append('links')
            else:
                ring, script_id, script_count = context
    except DB_ERRORS:
        unchecked.append('links')
    signals = list(base_signals)
    if 'links' not in unchecked:
        kinds = [v for v in ring.via if v != 'same_script']
        if kinds:
            signals.append(signal('S4', min(weights.S4_CAP, len(kinds) * weights.S4_PER_TYPE),
                'Linked to earlier reports', f'{ring.linked_checks} earlier high-risk or reported checks share the same '
                + ', '.join(LINK_NAMES.get(k, k) for k in kinds)))
        if script_count:
            signals.append(signal('S5', weights.S5, 'Matching message script',
                                   f'{script_count} earlier high-risk or reported checks match this script'))
    signals.sort(key=lambda s: s.id)
    total, band = score(signals)
    unchecked = sorted(set(unchecked))
    headline, explanation, steps = language.fallback(band, body.lang, unchecked)
    localized = language.localize(signals, body.lang)
    generated = await bounded(llm.explain(signals, band, body.lang, unchecked),
                              min(1.5, deadline - time.perf_counter() - 0.25))
    explained = bool(generated and not re.search(r'\b(?:safe|genuine|scammer)\b|100\s*%|सुरक्षित', generated.explanation, re.I))
    if explained:
        explanation = mask_text(generated.explanation)
        # Lookup translations may change words, never source facts, numbers or quote evidence.
        if [s.id for s in generated.signals] == [s.id for s in signals]:
            for i, (original, translated) in enumerate(zip(signals, generated.signals)):
                facts = re.findall(r'\d+|[\w.-]+\.[a-z]{2,}|\w*…@\w+', original.evidence.text)
                if original.evidence.kind == 'lookup' and all(f in translated.evidence for f in facts):
                    localized[i] = original.model_copy(update={'label':mask_text(translated.label),
                        'evidence':original.evidence.model_copy(update={'text':mask_text(translated.evidence)})})
    # Otherwise the fixed, localized fallback text stands. It is not a signal, so it never goes in `unchecked`,
    # but it isn't cached either: the next identical check should get the model's explanation once it recovers.
    result = CheckResponse(check_id=check_id, band=band, score=total, lang=body.lang,
        headline=headline, explanation=explanation, signals=localized, entities=display_entities(extracted),
        ring=ring, next_steps=steps, share=Share(url=share_url, card_title=headline), transcript=transcript,
        unchecked=unchecked, cached=False, latency_ms=int((time.perf_counter() - started) * 1000))
    # Apply the public redaction guard before persistence and response serialization.
    result = CheckResponse(**public_view(result).model_dump())
    try:
        await asyncio.to_thread(db.save_check, path, result, records, embedding or None, script_id,
                                key, body.anon_id, inp.input_type, created, body.ref, cacheable=explained)
    except DB_ERRORS:
        result.unchecked = sorted(set(result.unchecked + ['links']))
        result.signals = [s for s in result.signals if s.id not in ('S4','S5')]
        result.score, result.band = score(result.signals)
        result.ring = Ring(linked_checks=0, linked_reports=0, via=[])
        result.headline, result.explanation, result.next_steps = language.fallback(result.band, body.lang, result.unchecked)
        result.share.card_title = result.headline
    consent_buffer.put(check_id, body.anon_id, text)
    result.latency_ms = int((time.perf_counter() - started) * 1000)
    return result
