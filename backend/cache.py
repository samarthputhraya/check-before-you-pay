"""Canonical cache keys and bounded, ephemeral consent handoff. No raw input goes to disk."""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from threading import Lock

from backend.extraction import normalize, regex_extract
from backend.inputs import ValidInput


def input_hash(inp: ValidInput) -> str:
    entities = regex_extract(inp.text or '').entities
    # Prose and UPI handles are case insensitive; URL paths/invites and non-EVM
    # addresses are not. Keep those distinctions inside the digest only.
    case_sensitive = [entities.urls,
                      [w for w in entities.wallet_addresses if not w.startswith('0x')]]
    payload = [normalize(inp.text or ''), inp.image_mime, inp.audio_mime,
               hashlib.sha256(inp.image).hexdigest() if inp.image else None,
               hashlib.sha256(inp.audio).hexdigest() if inp.audio else None, case_sensitive]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


class ConsentBuffer:
    """15-minute volatile buffer, owner-bound and capped at 500 entries (max ~10 MB)."""
    def __init__(self) -> None:
        self._items: OrderedDict[tuple[str, str], tuple[float, str]] = OrderedDict()
        self._lock = Lock()

    def put(self, check_id: str, owner: str, text: str) -> None:
        with self._lock:
            self._prune()
            self._items[(check_id, owner)] = (time.monotonic(), text[:20_000])
            while len(self._items) > 500:
                self._items.popitem(last=False)

    def take(self, check_id: str, owner: str, consent: bool) -> str | None:
        with self._lock:
            self._prune()
            item = self._items.pop((check_id, owner), None)
            return item[1] if consent and item else None

    def peek(self, check_id: str, owner: str, consent: bool) -> str | None:
        """Read for a pending report; retain the text until its database write succeeds."""
        with self._lock:
            self._prune()
            item = self._items.get((check_id, owner))
            return item[1] if consent and item else None

    def _prune(self) -> None:
        now = time.monotonic()
        for key, (created, _) in list(self._items.items()):
            if now - created > 900:
                del self._items[key]


consent_buffer = ConsentBuffer()
