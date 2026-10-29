"""Validate and decode a /api/check input. Raises ApiError with the contract's error codes."""
from __future__ import annotations

import base64
import binascii
import re
import io
from dataclasses import dataclass

import mutagen
from PIL import Image, UnidentifiedImageError

from backend.config import AUDIO_MIMES, IMAGE_MIMES, MAX_FILE_BYTES, MAX_TEXT_CHARS
from backend.errors import ApiError
from backend.schemas import CheckInput

_DATA_URL = re.compile(r"^data:[\w.+/-]+;base64,", re.IGNORECASE)
# Longest base64 string that can still decode to MAX_FILE_BYTES (4 chars per 3 bytes, plus padding).
_MAX_B64_CHARS = (MAX_FILE_BYTES + 2) // 3 * 4


@dataclass(frozen=True)
class ValidInput:
    text: str | None
    image: bytes | None
    image_mime: str | None
    audio: bytes | None
    audio_mime: str | None

    @property
    def input_type(self) -> str:
        if self.image is not None:
            return "image"
        if self.audio is not None:
            return "audio"
        return "text"


def _decode(field: str, raw: str) -> bytes:
    raw = _DATA_URL.sub("", raw.strip())
    raw = re.sub(r"\s+", "", raw)
    if len(raw) > _MAX_B64_CHARS:
        raise ApiError(413, "input_too_large", "Files can be at most 5 MB.")
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(400, "invalid_request", f"{field} is not valid base64.") from None
    if len(data) > MAX_FILE_BYTES:
        raise ApiError(413, "input_too_large", "Files can be at most 5 MB.")
    if not data:
        raise ApiError(400, "invalid_request", f"{field} is empty.")
    return data


def _image_matches(mime: str, data: bytes) -> bool:
    if mime == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    return data.startswith(b"\xff\xd8\xff")  # image/jpeg


def _audio_matches(mime: str, data: bytes) -> bool:
    if mime == "audio/ogg":
        return data.startswith(b"OggS")
    if mime == "audio/mp4":
        return data[4:8] == b"ftyp"
    # audio/mpeg: an ID3 tag, or an MPEG frame sync (11 set bits).
    return data.startswith(b"ID3") or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)


_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")  # zero-width characters


def _clean_text(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        raw.encode("utf-8")
    except UnicodeEncodeError:  # a lone surrogate can't be hashed or stored
        raise ApiError(400, "invalid_request", "The message contains characters that aren't valid text.") from None
    return _ZERO_WIDTH.sub("", raw).strip() or None


def validate_check_input(inp: CheckInput) -> ValidInput:
    text = _clean_text(inp.text)
    if text is None and not inp.image_b64 and not inp.audio_b64:
        raise ApiError(400, "empty_input", "Send a message, a screenshot or a voice note to check.")
    if text is not None and len(text) > MAX_TEXT_CHARS:
        raise ApiError(413, "input_too_large", f"Messages can be at most {MAX_TEXT_CHARS:,} characters.")

    image = audio = None
    if inp.image_b64:
        if inp.image_mime not in IMAGE_MIMES:
            raise ApiError(415, "unsupported_media", "Screenshots must be PNG or JPEG.")
        image = _decode("image_b64", inp.image_b64)
        if not _image_matches(inp.image_mime, image):
            raise ApiError(415, "unsupported_media", f"The file is not a valid {inp.image_mime.split('/')[1].upper()} image.")
        try:
            with Image.open(io.BytesIO(image)) as screenshot:
                if screenshot.width * screenshot.height > 25_000_000:
                    raise ApiError(413, 'input_too_large', 'Screenshots can be at most 25 megapixels.')
                screenshot.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise ApiError(415, 'unsupported_media', 'The screenshot could not be read. Send a PNG or JPEG image.') from None
    if inp.audio_b64:
        if inp.audio_mime not in AUDIO_MIMES:
            raise ApiError(415, "unsupported_media", "Voice notes must be OGG, M4A or MP3.")
        audio = _decode("audio_b64", inp.audio_b64)
        if not _audio_matches(inp.audio_mime, audio):
            raise ApiError(415, "unsupported_media", "The file does not look like the audio type it claims to be.")
        try:
            parsed = mutagen.File(io.BytesIO(audio))
            if parsed is None or not parsed.info.length or parsed.info.length < 0:
                raise ValueError('Unreadable audio')
            if parsed.info.length > 120:
                raise ApiError(413, 'input_too_large', 'Voice notes can be at most 2 minutes.')
        except (mutagen.MutagenError, OSError, ValueError):
            raise ApiError(415, 'unsupported_media', 'The voice note could not be read. Send an OGG, M4A or MP3 file.') from None

    return ValidInput(text=text, image=image, image_mime=inp.image_mime if image else None,
                      audio=audio, audio_mime=inp.audio_mime if audio else None)
