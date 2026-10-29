"""Internal extraction types and source verification; none changes the public contract."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import tldextract
from pydantic import BaseModel, Field

ClaimType = Literal['guaranteed_returns', 'vip_or_institutional_account', 'ipo_allotment',
                    'urgency_pressure', 'sebi_registered_claim', 'install_app_or_apk',
                    'withdrawal_fee', 'impersonates_brand', 'other']


class Claim(BaseModel):
    type: ClaimType
    quote: str = Field(max_length=1000)


class ExtractedEntities(BaseModel):
    upi_ids: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    wallet_addresses: list[str] = Field(default_factory=list)
    group_links: list[str] = Field(default_factory=list)
    app_names: list[str] = Field(default_factory=list)
    sebi_reg_numbers: list[str] = Field(default_factory=list)


class Extraction(BaseModel):
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    claims: list[Claim] = Field(default_factory=list)


ZERO_WIDTH = re.compile('[\u200b\u200c\u200d\u2060\ufeff]')
# A full stop may end the sentence ("…@ybl." or "…@ybl.Thanks"); an email's ".com" or ".COM" may not.
UPI = re.compile(r'(?<![\w@])([\w][\w.\-]{1,255}@[a-zA-Z][a-zA-Z0-9]{1,30})(?![\w@]|\.[a-z0-9]|\.(?i:com|in|org|net|co|gov|edu|io)\b)')
PHONE = re.compile(r'(?<!\w)(?:\+?91[\s-]?)?([6-9](?:[\s-]?\d){9})(?!\w)')
WALLET = re.compile(r'\b(?:0x[0-9a-fA-F]{40}|T[1-9A-HJ-NP-Za-km-z]{33}|bc1[ac-hj-np-z02-9]{25,62}|[13][1-9A-HJ-NP-Za-km-z]{25,34})\b')
URL = re.compile(r'https?://[^\s<>"\[\]{}]+', re.I)
BARE_DOMAIN = re.compile(r'(?<![\w@./-])(?:[a-zA-Z0-9\u0080-\uffff][a-zA-Z0-9\u0080-\uffff-]*\.)+[a-zA-Z]{2,63}(?![\w@-])(?:/[^\s<>"\[\]{}]*)?')
SEBI = re.compile(r'\bIN[A-Z]{1,3}\d{8,12}\b', re.I)
GROUP_HOSTS = frozenset(('t.me', 'telegram.me', 'chat.whatsapp.com'))
# Bundled PSL only: no network or disk writes on a request.
PSL = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
# Hosts shared by millions of unrelated pages. A link to one is not a link between two checks.
SHARED_HOSTS = frozenset({'t.me', 'telegram.me', 'telegram.org', 'wa.me', 'whatsapp.com', 'google.com', 'youtube.com',
                          'youtu.be', 'forms.gle', 'goo.gl', 'bit.ly', 'tinyurl.com', 'instagram.com', 'facebook.com',
                          'fb.me', 'x.com', 'twitter.com', 'linkedin.com', 'apple.com', 'amzn.to', 'cutt.ly', 'rb.gy',
                          'is.gd'})
_DIRECTIVE = re.compile(r'ignore\s+(?:all\s+)?(?:your|previous|prior)\s+instructions?[^\n.!?]*(?:[.!?]|$)', re.I)


def normalize(text: str) -> str:
    return ' '.join(ZERO_WIDTH.sub('', unicodedata.normalize('NFKC', text)).lower().split())


def source_text(text: str) -> str:
    """Remove the explicit adversarial directive from extraction/scoring, never follow it."""
    return _DIRECTIVE.sub('', ZERO_WIDTH.sub('', text)).strip()


def canonical_url(value: str) -> str | None:
    try:
        parts = urlsplit(value if '://' in value else 'https://' + value)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        host = parts.hostname.encode('idna').decode().lower().rstrip('.')
        if not PSL(host).suffix:
            return None
        port = parts.port
        netloc = host + (f':{port}' if port and port not in (80, 443) else '')
        return urlunsplit((parts.scheme, netloc, parts.path or '/', parts.query, ''))
    except (ValueError, UnicodeError):
        return None


def registered_domain(host: str) -> str:
    return PSL(host).top_domain_under_public_suffix or host


def link_host(host: str) -> str | None:
    """The host a domain link is keyed on: no www., and None for shared platforms such as t.me or drive.google.com."""
    host = host.lower().rstrip('.').removeprefix('www.')
    return None if host in SHARED_HOSTS or registered_domain(host) in SHARED_HOSTS else host


def regex_extract(text: str) -> Extraction:
    text = source_text(text)
    urls = set()
    upis = list(UPI.finditer(text))
    explicit_urls = list(URL.finditer(text))
    occupied = [m.span() for m in upis + explicit_urls]
    bare_urls = [m for m in BARE_DOMAIN.finditer(text)
                 if not any(m.start() < end and m.end() > start for start, end in occupied)]
    for match in explicit_urls + bare_urls:
        candidate = match.group().rstrip('.,;:!?)')
        url = canonical_url(candidate)
        if url:
            urls.add(url)
    groups = [u for u in urls if urlsplit(u).hostname in GROUP_HOSTS and urlsplit(u).path != '/']
    wallets = sorted(set(WALLET.findall(text)))
    without_wallets = WALLET.sub('', text)
    return Extraction(entities=ExtractedEntities(
        upi_ids=sorted({normalize(m.group(1)) for m in upis}),
        phones=sorted({re.sub(r'\D', '', v) for v in PHONE.findall(without_wallets)}),
        urls=sorted(urls), domains=sorted({urlsplit(u).hostname for u in urls}),
        wallet_addresses=wallets, group_links=sorted(groups),
        sebi_reg_numbers=sorted(set(SEBI.findall(text.upper()))),
    ))


def verified_extraction(result: Extraction, text: str) -> Extraction:
    """AI claims need literal source support. Entities are independently extracted, never trusted."""
    clean = source_text(text)
    source = normalize(clean)
    verified = regex_extract(clean)
    seen = set()
    for claim in result.claims:
        quote = normalize(claim.quote)
        key = (claim.type, quote)
        if quote and quote in source and key not in seen:
            verified.claims.append(claim)
            seen.add(key)
    verified.entities.app_names = sorted({a for a in result.entities.app_names
                                          if 1 < len(a) <= 100 and normalize(a) in source})
    return verified
