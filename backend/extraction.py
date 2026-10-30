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
                    'withdrawal_fee', 'insider_tip', 'task_deposit', 'recovery_fee',
                    'impersonates_brand', 'other']


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
BARE_DOMAIN = re.compile(r'(?<![\w@./-])(?:[a-zA-Z0-9\u0080-\uffff][a-zA-Z0-9\u0080-\uffff-]*\.)+[a-zA-Z]{2,63}(?![\w@-]|\.[\w])(?:/[^\s<>"\[\]{}]*)?')
SEBI = re.compile(r'\bIN[A-Z]{1,3}\d{8,12}\b', re.I)
GROUP_HOSTS = frozenset(('t.me', 'telegram.me', 'chat.whatsapp.com'))
SHARED_HOSTS = GROUP_HOSTS | frozenset(('drive.google.com', 'docs.google.com', 'youtube.com',
    'www.youtube.com', 'youtu.be', 'bit.ly', 'tinyurl.com', 'linktr.ee'))
# Bundled PSL only: no network or disk writes on a request.
PSL = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
_DIRECTIVE = re.compile(r'ignore\s+(?:all\s+)?(?:your|previous|prior)\s+instructions?[^\n.!?]*(?:[.!?]|$)', re.I)


# Voice notes dictate payment IDs ("stockpro dot desk at ybl"). Only a known UPI handle after "at", and a name that
# was spelled with a dot or is a 10-digit number, is rewritten, so "pay at paytm" or "meet at sbi" stay as said.
_PSP = (r'ybl|ibl|axl|okaxis|okhdfcbank|okicici|oksbi|paytm|ptyes|ptaxis|pthdfc|ptsbi|apl|yapl|rapl|abfspay|axisbank|'
        r'icici|hdfcbank|sbi|kotak|idfcbank|upi|freecharge|jupiteraxis|naviaxis|waaxis|wahdfcbank|waicici|wasbi|airtel|'
        r'jio|valid\w*')
_SPOKEN_ID = re.compile(r'(?<![\w@.])([A-Za-z0-9_][\w-]{0,40}(?:(?:\.|\s+(?:dot|डॉट)\s+)[\w-]{1,40}){0,4})\s+(?:at|एट|ऐट)\s+'
                        r'(' + _PSP + r')\b', re.I)
_SPOKEN_DOT = re.compile(r'\s*(?:\.|\bdot\b|डॉट)\s*', re.I)


# SEBI's handles are @valid plus the bank's name (@validhdfc, @validicici). Scammers imitate the word itself, so
# a bare "@valid", or "valid" plus a generic word ("@validupi", "@valid-upi" read as "@valid"), is not one.
# Banks that issue @valid handles to SEBI-registered intermediaries (circular of 11 June 2025, section 2.1, and the
# NPCI list). A bank we've missed shows S1 with "verify on SEBI Check", never a false "it's fine".
_VALID_BANKS = frozenset(('hdfc', 'icici', 'sbi', 'axis', 'kotak', 'yes', 'yesbank', 'idfc', 'idfcfirst', 'indus',
                          'indusind', 'bob', 'pnb', 'canara', 'union', 'ubi', 'boi', 'idbi', 'federal', 'rbl', 'au',
                          'aubank', 'hsbc', 'sc', 'scb', 'citi', 'dbs', 'kvb', 'tmb', 'csb', 'dcb', 'iob', 'indian',
                          'bandhan', 'equitas', 'ujjivan', 'jkb', 'sib', 'karnataka', 'cub', 'uco', 'centralbank'))


def sebi_valid_handle(upi_id: str) -> bool:
    handle = upi_id.rsplit('@', 1)[-1].lower()
    return handle.startswith('valid') and handle[5:] in _VALID_BANKS


def written_ids(transcript: str) -> str:
    def rewrite(m: re.Match) -> str:
        name = m.group(1)
        spelled = re.search(r'[A-Za-z]', name) and _SPOKEN_DOT.search(name)
        if not spelled and not re.fullmatch(r'\d{10}', name):
            return m.group(0)
        return _SPOKEN_DOT.sub('.', name) + '@' + m.group(2).lower()
    return _SPOKEN_ID.sub(rewrite, transcript)


def _pictograph(ch: str) -> bool:
    # Emoji and their modifiers; currency (₹), maths and punctuation stay.
    return unicodedata.category(ch) == 'So' or ch == '\ufe0f' or 0x1F3FB <= ord(ch) <= 0x1F3FF


def normalize(text: str) -> str:
    text = ZERO_WIDTH.sub('', unicodedata.normalize('NFKC', text))
    return ' '.join(''.join(' ' if _pictograph(ch) else ch for ch in text).lower().split())


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
        default_port = 80 if parts.scheme == 'http' else 443
        netloc = host + (f':{port}' if port and port != default_port else '')
        return urlunsplit((parts.scheme, netloc, parts.path or '/', parts.query, ''))
    except (ValueError, UnicodeError):
        return None


def registered_domain(host: str) -> str:
    return PSL(host).top_domain_under_public_suffix or host


def regex_extract(text: str) -> Extraction:
    text = source_text(text)
    urls = set()
    upis = []
    for match in UPI.finditer(text):
        # Capitalized sentence text may follow a UPI's full stop, but a real
        # email suffix (including .DE/.UK/etc.) must not turn into a UPI.
        continuation = re.match(r'\.[a-zA-Z0-9.-]+', text[match.end():])
        if continuation:
            host = match.group(1).split('@')[-1] + continuation.group().rstrip('.')
            if PSL(host).suffix:
                continue
        upis.append(match)
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
