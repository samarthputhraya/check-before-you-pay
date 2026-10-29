"""All SQLite access: WAL, parameterized SQL, bounded transactions, online backups."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np

from backend.ids import new_id
from backend.links import Embedding, Identifier, connected_groups, cosine
from backend.schemas import CheckResponse, CheckView, EventRequest, Ring, StatsResponse
from backend.weights import SCRIPT_SIMILARITY

SCHEMA = '''
CREATE TABLE IF NOT EXISTS checks (
 id TEXT PRIMARY KEY, created_at REAL NOT NULL, band TEXT NOT NULL, score INTEGER NOT NULL,
 lang TEXT NOT NULL, input_type TEXT NOT NULL, anon_id TEXT NOT NULL, script_id TEXT,
 response_json TEXT NOT NULL, input_hash TEXT NOT NULL, is_sample INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, type TEXT NOT NULL, masked TEXT NOT NULL, meta_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS check_entities (
 check_id TEXT NOT NULL REFERENCES checks(id), entity_id TEXT NOT NULL REFERENCES entities(id),
 PRIMARY KEY(check_id, entity_id));
CREATE INDEX IF NOT EXISTS by_entity ON check_entities(entity_id, check_id);
CREATE TABLE IF NOT EXISTS scripts (
 id TEXT PRIMARY KEY, embedding_blob BLOB NOT NULL, sample_count INTEGER NOT NULL, model TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS by_script ON checks(script_id);
CREATE TABLE IF NOT EXISTS reports (
 id TEXT PRIMARY KEY, check_id TEXT NOT NULL REFERENCES checks(id), created_at REAL NOT NULL,
 text_if_consented TEXT, anon_id TEXT NOT NULL, note TEXT,
 webhook_status TEXT NOT NULL DEFAULT 'pending', webhook_attempts INTEGER NOT NULL DEFAULT 0,
 webhook_after REAL NOT NULL DEFAULT 0, UNIQUE(check_id, anon_id));
CREATE TABLE IF NOT EXISTS cache (
 input_hash TEXT NOT NULL, lang TEXT NOT NULL, check_id TEXT NOT NULL REFERENCES checks(id),
 created_at REAL NOT NULL, PRIMARY KEY(input_hash, lang));
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, anon_id TEXT NOT NULL, event TEXT NOT NULL, check_id TEXT, ref TEXT,
 props_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS by_event ON events(event, created_at);
CREATE TABLE IF NOT EXISTS quiz_results (
 id TEXT PRIMARY KEY, anon_id TEXT NOT NULL, quiz_id TEXT NOT NULL, score INTEGER NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rate_limits (bucket TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS rate_bucket ON rate_limits(bucket, created_at);
'''


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=0.25)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=250')
    con.execute('PRAGMA foreign_keys=ON')
    deadline = time.monotonic() + 1.8
    con.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    return con


@contextmanager
def session(path: Path) -> Iterator[sqlite3.Connection]:
    con = connect(path)
    try:
        con.executescript(SCHEMA)
        with con:
            yield con
    finally:
        con.close()


def ping(path: Path) -> bool:
    try:
        with session(path) as con:
            con.execute('BEGIN IMMEDIATE')
        return True
    except (sqlite3.Error, OSError):
        return False


def get_check(path: Path, check_id: str) -> CheckView | None:
    with session(path) as con:
        row = con.execute('SELECT response_json FROM checks WHERE id=?', (check_id,)).fetchone()
        return CheckView.model_validate_json(row[0]) if row else None


def cached_check(path: Path, key: str, lang: str, now: float | None = None) -> CheckView | None:
    with session(path) as con:
        row = con.execute('''SELECT c.response_json FROM cache k JOIN checks c ON c.id=k.check_id
                             WHERE k.input_hash=? AND k.lang=? AND k.created_at>?''',
                          (key, lang, (now or time.time()) - 86400)).fetchone()
        return CheckView.model_validate_json(row[0]) if row else None


def _ring(con: sqlite3.Connection, ids: list[str], before: float, exclude: str = '', script_id: str | None = None) -> Ring:
    linked: dict[str, set[str]] = {}
    if ids:
        placeholders = ','.join('?' for _ in ids)
        rows = con.execute(f'''SELECT c.id,e.type FROM checks c JOIN check_entities ce ON ce.check_id=c.id
             JOIN entities e ON e.id=ce.entity_id WHERE e.id IN ({placeholders}) AND c.created_at<? AND c.id!=?
             AND (c.band='high_risk' OR EXISTS(SELECT 1 FROM reports r WHERE r.check_id=c.id))''',
                           (*ids, before, exclude)).fetchall()
        for row in rows:
            if row['type'] in ('upi', 'phone', 'domain', 'group_link', 'wallet'):
                linked.setdefault(row['id'], set()).add('same_' + row['type'])
    if script_id:
        rows = con.execute('''SELECT id FROM checks c WHERE script_id=? AND created_at<? AND id!=?
            AND (band='high_risk' OR EXISTS(SELECT 1 FROM reports r WHERE r.check_id=c.id))''',
                           (script_id, before, exclude)).fetchall()
        for row in rows:
            linked.setdefault(row['id'], set()).add('same_script')
    reports = 0
    if linked:
        reports = con.execute(f"SELECT COUNT(*) FROM reports WHERE check_id IN ({','.join('?' for _ in linked)})",
                              tuple(linked)).fetchone()[0]
    return Ring(linked_checks=len(linked), linked_reports=reports,
                via=sorted(set().union(*linked.values())) if linked else [])


def ring_for_check(path: Path, check_id: str) -> Ring:
    with session(path) as con:
        row = con.execute('SELECT created_at,script_id FROM checks WHERE id=?', (check_id,)).fetchone()
        if not row:
            return Ring(linked_checks=0, linked_reports=0, via=[])
        ids = [r[0] for r in con.execute('SELECT entity_id FROM check_entities WHERE check_id=?', (check_id,))]
        return _ring(con, ids, row['created_at'], check_id, row['script_id'])


def link_context(path: Path, identifiers: list[Identifier], embedding: Embedding | None,
                 before: float) -> tuple[Ring, str | None, int]:
    with session(path) as con:
        script_id = None
        count = 0
        if embedding:
            best = SCRIPT_SIMILARITY
            for row in con.execute('SELECT id,embedding_blob FROM scripts WHERE model=? ORDER BY id', (embedding.model,)):
                similarity = cosine(embedding.values, np.frombuffer(row['embedding_blob'], dtype='<f4').tolist())
                if similarity >= best:
                    best, script_id = similarity, row['id']
            if script_id:
                count = con.execute('''SELECT COUNT(*) FROM checks c WHERE script_id=? AND created_at<?
                    AND (band='high_risk' OR EXISTS(SELECT 1 FROM reports r WHERE r.check_id=c.id))''',
                                    (script_id, before)).fetchone()[0]
        return _ring(con, [i.id for i in identifiers], before, script_id=script_id), script_id, count


def save_check(path: Path, result: CheckResponse, identifiers: list[Identifier], embedding: Embedding | None,
               script_id: str | None, key: str, anon_id: str, input_type: str, created: float,
               ref: str | None = None, sample: bool = False) -> None:
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if embedding:
            script_id = script_id or new_id('scr')
            vector = np.asarray(embedding.values, dtype='<f4')
            if vector.ndim != 1 or not vector.size or not np.isfinite(vector).all():
                raise ValueError('Invalid embedding')
            con.execute('''INSERT INTO scripts(id,embedding_blob,sample_count,model) VALUES (?,?,1,?)
                ON CONFLICT(id) DO UPDATE SET sample_count=sample_count+1''',
                        (script_id, vector.tobytes(), embedding.model))
        elif result.cached:
            source = con.execute('SELECT c.script_id FROM cache k JOIN checks c ON c.id=k.check_id WHERE k.input_hash=? AND k.lang=?',
                                 (key, result.lang)).fetchone()
            script_id = source[0] if source else None
        con.execute('''INSERT INTO checks
                    (id,created_at,band,score,lang,input_type,anon_id,script_id,response_json,input_hash,is_sample)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (result.check_id, created, result.band, result.score, result.lang, input_type, anon_id,
                     script_id, result.model_dump_json(exclude={'transcript'}), key, int(sample)))
        for entity in identifiers:
            con.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?,?)',
                        (entity.id, entity.type, entity.masked, json.dumps(entity.meta)))
            con.execute('INSERT OR IGNORE INTO check_entities VALUES (?,?)', (result.check_id, entity.id))
        if result.cached:
            con.execute('''INSERT OR IGNORE INTO check_entities SELECT ?,ce.entity_id FROM cache k
                JOIN check_entities ce ON ce.check_id=k.check_id WHERE k.input_hash=? AND k.lang=?''',
                        (result.check_id, key, result.lang))
        # Hits do not refresh TTL. Partial failures must not become a 24-hour answer.
        if not result.cached and not result.unchecked and not sample:
            con.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?,?)', (key, result.lang, result.check_id, created))
        if not sample:
            _event(con, EventRequest(anon_id=anon_id, event='check_done', check_id=result.check_id, ref=ref,
                                    props={'latency_ms': result.latency_ms, 'band': result.band,
                                           'lang': result.lang, 'input_type': input_type}), created)


def entity_history(path: Path, entity_id: str) -> list[dict]:
    with session(path) as con:
        return [dict(r) for r in con.execute('''SELECT c.id,c.created_at,c.band,c.score,
            (SELECT COUNT(*) FROM reports r WHERE r.check_id=c.id) AS reports
            FROM checks c JOIN check_entities ce ON ce.check_id=c.id WHERE ce.entity_id=? ORDER BY c.created_at''', (entity_id,))]


def add_report(path: Path, check_id: str, anon_id: str, text: str | None, note: str | None) -> tuple[str, bool]:
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if not con.execute('SELECT 1 FROM checks WHERE id=?', (check_id,)).fetchone():
            raise KeyError(check_id)
        existing = con.execute('SELECT id FROM reports WHERE check_id=? AND anon_id=?', (check_id, anon_id)).fetchone()
        if existing:
            return existing[0], False
        report_id = new_id('rep')
        con.execute('INSERT INTO reports(id,check_id,created_at,text_if_consented,anon_id,note) VALUES (?,?,?,?,?,?)',
                    (report_id, check_id, time.time(), text, anon_id, note))
        con.execute('DELETE FROM cache')  # New reports change the available evidence.
        _event(con, EventRequest(anon_id=anon_id, event='report', check_id=check_id), time.time())
        return report_id, True


def _event(con: sqlite3.Connection, body: EventRequest, now: float) -> None:
    props = {k: v for k, v in body.props.items() if k in ('latency_ms', 'band', 'lang', 'input_type', 'score')}
    con.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                (new_id('evt'), body.anon_id, body.event, body.check_id, body.ref, json.dumps(props), now))


def record_event(path: Path, body: EventRequest) -> None:
    if body.event in ('check_done', 'report'):
        return  # These are authoritative server events; ignore client copies.
    with session(path) as con:
        if body.event in ('visit', 'ref_visit', 'return_visit') and con.execute(
                'SELECT 1 FROM events WHERE anon_id=? AND event=? AND created_at>? LIMIT 1',
                (body.anon_id, body.event, time.time() - 3600)).fetchone():
            return
        _event(con, body, time.time())


def allow_request(path: Path, buckets: list[tuple[str, int]], now: float | None = None) -> bool:
    now = now or time.time()
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM rate_limits WHERE created_at<=?', (now - 3600,))
        for bucket, limit in buckets:
            if con.execute('SELECT COUNT(*) FROM rate_limits WHERE bucket=?', (bucket,)).fetchone()[0] >= limit:
                return False
        con.executemany('INSERT INTO rate_limits VALUES (?,?)', [(b, now) for b, _ in buckets])
        return True


def top_rings(path: Path, k: int | None = 10, include_samples: bool = False) -> list[list[str]]:
    with session(path) as con:
        rows = con.execute('''SELECT c.id,ce.entity_id FROM checks c JOIN check_entities ce ON ce.check_id=c.id
            JOIN entities e ON e.id=ce.entity_id WHERE c.band='high_risk' AND (? OR c.is_sample=0)
            AND e.type IN ('upi','phone','domain','group_link','wallet')''', (include_samples,)).fetchall()
        scripts = con.execute("SELECT id,'script:'||script_id FROM checks WHERE band='high_risk' AND script_id IS NOT NULL AND (? OR is_sample=0)",
                              (include_samples,)).fetchall()
        return connected_groups([(r[0], r[1]) for r in [*rows, *scripts]], k)


def stats(path: Path) -> StatsResponse:
    with session(path) as con:
        checks = con.execute('SELECT id,anon_id,lang,response_json FROM checks WHERE is_sample=0').fetchall()
        users = {r['anon_id'] for r in checks}
        users.update(r[0] for r in con.execute('SELECT DISTINCT anon_id FROM events'))
        languages: dict[str, int] = {}
        latencies = []
        for row in checks:
            languages[row['lang']] = languages.get(row['lang'], 0) + 1
            latencies.append(json.loads(row['response_json'])['latency_ms'])
        reports = con.execute('SELECT COUNT(*) FROM reports r JOIN checks c ON c.id=r.check_id WHERE c.is_sample=0').fetchone()[0]
        shared = con.execute("SELECT COUNT(DISTINCT e.check_id) FROM events e JOIN checks c ON c.id=e.check_id WHERE e.event='share_clicked' AND c.is_sample=0").fetchone()[0]
        sharers = {r[0] for r in con.execute("SELECT DISTINCT anon_id FROM events WHERE event IN ('share_clicked','quiz_shared')")}
        referred = {r[0] for r in con.execute("SELECT DISTINCT anon_id,ref FROM events WHERE event='ref_visit' AND ref IS NOT NULL AND ref!=anon_id") if r[1] in sharers}
    return StatsResponse(users=len(users), checks=len(checks), reports=reports, languages=languages,
                         rings=len(top_rings(path, None)), share_rate=shared / len(checks) if checks else 0,
                         k_factor=len(referred) / len(sharers) if sharers else 0,
                         p50_ms=int(np.percentile(latencies, 50)) if latencies else 0,
                         p95_ms=int(np.percentile(latencies, 95)) if latencies else 0,
                         updated_at=datetime.now(timezone.utc).isoformat())


def pending_webhooks(path: Path) -> list[dict]:
    with session(path) as con:
        return [dict(r) for r in con.execute('''SELECT id,check_id FROM reports WHERE webhook_status='pending'
            AND webhook_attempts<3 AND webhook_after<=? ORDER BY created_at LIMIT 10''', (time.time(),))]


def webhook_result(path: Path, report_id: str, delivered: bool) -> None:
    with session(path) as con:
        con.execute('''UPDATE reports SET webhook_attempts=webhook_attempts+1,
            webhook_status=CASE WHEN ? THEN 'delivered' WHEN webhook_attempts>=2 THEN 'failed' ELSE 'pending' END,
            webhook_after=? WHERE id=?''', (delivered, time.time() + 60, report_id))


def export_database(path: Path) -> bytes:
    with session(path) as source:
        with sqlite3.connect(':memory:') as target:
            source.backup(target)
            return target.serialize()
