from __future__ import annotations

import asyncio
import io
import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

import discord
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from mute_bot.config import OCR_ENABLED, OCR_EXTENSIONS, OCR_MAX_BYTES
from mute_bot.data.responses import BANNED_TERMS, CHAR_EQ

log = logging.getLogger("Mute")


def build_banned_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []

    for term in BANNED_TERMS:
        parts: list[str] = []

        for character in term:
            equivalents = re.escape(CHAR_EQ.get(character, character))
            parts.append(f"[{equivalents}]")

        body = r"[\W_]*".join(parts)

        if term == "rape":
            # Match "rape" and "raped", including the existing leet/spacing handling,
            # but do not match words where it is embedded, such as "trapped".
            pattern = re.compile(
                rf"(?<![A-Za-z0-9]){body}(?:[\W_]*d)?(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
        else:
            pattern = re.compile(
                rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
        patterns.append((term, pattern))

    return patterns


BANNED_PATTERNS = build_banned_patterns()


def normalize_filter_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\|\s*[\\/]\s*\|", "n", text)
    text = re.sub(r"/\s*\\", "n", text)
    text = re.sub(r"\\\s*/", "n", text)
    text = text.replace("η", "n").replace("ո", "n").replace("п", "n")
    text = text.replace("і", "i").replace("ı", "i").replace("ⅼ", "l")
    text = text.replace("ɡ", "g").replace("ց", "g")
    text = text.replace("а", "a").replace("е", "e").replace("о", "o")
    return "".join(ch for ch in text if ch not in "\u200b\u200c\u200d\ufeff")


def find_banned_term(text: str) -> Optional[str]:
    cleaned = normalize_filter_text(text)
    for term, pattern in BANNED_PATTERNS:
        if pattern.search(cleaned):
            return term
    return None


def preprocess_ocr(image_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("L")

    width, height = image.size
    longest = max(width, height)

    if longest < 1800:
        factor = min(3.0, 1800 / max(1, longest))
        image = image.resize(
            (int(width * factor), int(height * factor)),
            Image.Resampling.LANCZOS,
        )

    image = ImageEnhance.Contrast(image).enhance(2.0)
    return image.filter(ImageFilter.SHARPEN)


def run_ocr(image_bytes: bytes, *, ocr_enabled: Optional[bool] = None) -> str:
    enabled = OCR_ENABLED if ocr_enabled is None else ocr_enabled
    if not enabled:
        return ""

    return pytesseract.image_to_string(
        preprocess_ocr(image_bytes),
        config="--oem 3 --psm 6",
    )


async def attachment_banned_term(
    message: discord.Message,
    *,
    ocr_enabled: Optional[bool] = None,
) -> Optional[str]:
    enabled = OCR_ENABLED if ocr_enabled is None else ocr_enabled
    if not enabled:
        return None

    for attachment in message.attachments:
        extension = Path(attachment.filename).suffix.lower()

        if extension not in OCR_EXTENSIONS:
            continue
        if attachment.size > OCR_MAX_BYTES:
            continue

        try:
            image_bytes = await attachment.read()
            text = await asyncio.to_thread(run_ocr, image_bytes, ocr_enabled=enabled)
            term = find_banned_term(text)

            if term:
                return term

        except pytesseract.TesseractNotFoundError:
            log.error("Tesseract executable was not found; OCR is disabled.")
            return None
        except Exception:
            log.exception("OCR failed for attachment %s.", attachment.id)

    return None
