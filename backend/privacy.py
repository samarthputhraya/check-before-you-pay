"""Masking for anything a public page or share card shows (BUILD_BRIEF section 13: masked values only).

Examples: tradepro.vip@ybl -> tr…@ybl, 9876543210 -> 98xxxxxx10, a crypto address -> its first 4 and last 4 characters.
"""
from __future__ import annotations

import re

from backend.schemas import CheckView

_UPI = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9._-]{1,})@([A-Za-z][A-Za-z0-9]{1,30})\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{9})(?!\d)")
_WALLET = re.compile(r"\b(0x[0-9a-fA-F]{40}|T[1-9A-HJ-NP-Za-km-z]{33}|(?:bc1|[13])[0-9A-HJ-NP-Za-z]{25,62})\b")


def mask_upi(upi: str) -> str:
    name, _, handle = upi.partition("@")
    return f"{name[:2]}…@{handle}"


def mask_phone(digits: str) -> str:
    return f"{digits[:2]}xxxxxx{digits[-2:]}"


def mask_text(text: str) -> str:
    """Mask every UPI ID, Indian mobile number and wallet address inside free text."""
    text = _WALLET.sub(lambda m: f"{m.group(1)[:4]}…{m.group(1)[-4:]}", text)
    text = _UPI.sub(lambda m: mask_upi(m.group(0)), text)
    return _PHONE.sub(lambda m: mask_phone(m.group(1)), text)


def public_view(view: CheckView) -> CheckView:
    """The masked copy of a check that /api/check/{id} and /c/{id} may show to anyone with the link."""
    signals = [sig.model_copy(update={"label": mask_text(sig.label),
                                      "evidence": sig.evidence.model_copy(update={"text": mask_text(sig.evidence.text)})})
               for sig in view.signals]
    return view.model_copy(update={
        "headline": mask_text(view.headline), "explanation": mask_text(view.explanation), "signals": signals,
        "share": view.share.model_copy(update={"card_title": mask_text(view.share.card_title)}),
    })
