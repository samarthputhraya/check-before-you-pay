"""Hashed entity records and pure ring/script helpers. SQLite operations live in db.py."""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import numpy as np

from backend.extraction import Extraction, GROUP_HOSTS
from backend.privacy import mask_phone, mask_upi
from backend.schemas import Entity


@dataclass(frozen=True)
class Identifier:
    id: str
    type: str
    masked: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Embedding:
    model: str
    values: list[float]


def identifier_id(kind: str, value: str) -> str:
    salt = os.getenv('IDENTIFIER_SALT', '').strip()
    if len(salt) < 32:
        raise ValueError('IDENTIFIER_SALT must be configured with at least 32 characters')
    return hmac.new(salt.encode(), f'{kind}\0{value}'.encode(), hashlib.sha256).hexdigest()


def identifiers(extraction: Extraction) -> list[Identifier]:
    result = []
    e = extraction.entities
    for kind, values in [('upi', e.upi_ids), ('phone', e.phones), ('domain', e.domains),
                         ('group_link', e.group_links), ('wallet', e.wallet_addresses), ('app', e.app_names)]:
        for value in sorted(set(values)):
            if kind == 'domain' and value in GROUP_HOSTS:
                continue  # A shared hosting service does not connect two different invite links.
            meta = {}
            if kind == 'upi':
                value = value.lower()
                masked = mask_upi(value)
                meta = {'psp': value.split('@')[-1], 'is_valid_handle': value.split('@')[-1].startswith('valid')}
            elif kind == 'phone':
                masked = mask_phone(value)
            elif kind == 'group_link':
                masked = f'{urlsplit(value).hostname}/…'
            elif kind == 'wallet':
                # Bitcoin/Tron are case sensitive; hexadecimal Ethereum addresses are not.
                if value.startswith('0x'):
                    value = value.lower()
                masked = f'{value[:4]}…{value[-4:]}'
            elif kind == 'domain':
                value = value.lower()
                masked = value
            else:
                masked = 'App mentioned'  # arbitrary model text is never persisted
            result.append(Identifier(identifier_id(kind, value), kind, masked, meta))
    return result


def display_entities(extraction: Extraction) -> list[Entity]:
    """Does not need the salt: a database/config outage must still allow a private verdict."""
    e = extraction.entities
    items = ([Entity(type='upi', masked=mask_upi(u)) for u in e.upi_ids]
             + [Entity(type='phone', masked=mask_phone(p)) for p in e.phones]
             + [Entity(type='domain', masked=d) for d in e.domains]
             + [Entity(type='group_link', masked=f'{urlsplit(g).hostname}/…') for g in e.group_links]
             + [Entity(type='wallet', masked=f'{w[:4]}…{w[-4:]}') for w in e.wallet_addresses])
    return items


def cosine(a: list[float], b: list[float]) -> float:
    x, y = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    if x.shape != y.shape or x.ndim != 1 or not x.size or not np.isfinite(x).all() or not np.isfinite(y).all():
        return 0.0
    denominator = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(np.dot(x, y) / denominator) if denominator else 0.0


def connected_groups(edges: list[tuple[str, str]], k: int | None = None) -> list[list[str]]:
    parent: dict[str, str] = {}

    def root(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first: dict[str, str] = {}
    for check_id, entity_id in edges:
        root(check_id)
        if entity_id in first:
            parent[root(check_id)] = root(first[entity_id])
        else:
            first[entity_id] = check_id
    groups: dict[str, list[str]] = {}
    for check_id in parent:
        groups.setdefault(root(check_id), []).append(check_id)
    ordered = sorted((sorted(g) for g in groups.values() if len(g) > 1), key=lambda g: (-len(g), g))
    return ordered if k is None else ordered[:k]
