from __future__ import annotations

import re
import time
from typing import Optional

import discord

from mute_bot.config import (
    EXALTED_FOUR_ROLE,
    MUTE_COOLDOWN_SECONDS,
    MUTE_GREETING_MAX_USES,
    MUTE_GREETING_WINDOW_SECONDS,
    WARDEN_ROLE,
)

MUTE_TEXT_MENTION_RE = re.compile(r"(?<![\w@])@mute(?!\w)", re.IGNORECASE)


def _strip_bot_mentions(text: str, bot_user_id: Optional[int]) -> str:
    if bot_user_id is not None:
        text = re.sub(
            rf"<@!?{bot_user_id}>",
            "",
            text,
            flags=re.IGNORECASE,
        )
    return MUTE_TEXT_MENTION_RE.sub("", text)


def normalize_mute_phrase(content: str, bot_user_id: Optional[int] = None) -> str:
    content = _strip_bot_mentions(content, bot_user_id)
    content = content.lower()
    content = re.sub(r"[.!?]+", "", content)
    content = re.sub(r"\s+", " ", content).strip()
    return content


def contains_mute_mention(
    message: discord.Message,
    bot_user_id: Optional[int] = None,
) -> bool:
    if bot_user_id is not None and bot_user_id in message.raw_mentions:
        return True
    if bot_user_id is not None and re.search(
        rf"<@!?{bot_user_id}>",
        message.content,
        re.IGNORECASE,
    ):
        return True
    return MUTE_TEXT_MENTION_RE.search(message.content) is not None


def is_only_mute_mention(
    content: str,
    bot_user_id: Optional[int] = None,
) -> bool:
    rest = _strip_bot_mentions(content, bot_user_id)
    return re.sub(r"[.!?\s]+", "", rest) == ""


def mute_question_text(
    content: str,
    bot_user_id: Optional[int] = None,
) -> str:
    text = _strip_bot_mentions(content, bot_user_id)
    return re.sub(r"\s+", " ", text).strip()


def is_mute_question(
    message: discord.Message,
    bot_user_id: Optional[int] = None,
) -> bool:
    if not contains_mute_mention(message, bot_user_id):
        return False
    return "?" in message.content


def mute_cooldown_exempt(member: discord.Member) -> bool:
    role_ids = {role.id for role in member.roles}
    return EXALTED_FOUR_ROLE in role_ids or WARDEN_ROLE in role_ids


def mute_cooldown_seconds(member: discord.Member) -> int:
    if mute_cooldown_exempt(member):
        return 0
    return MUTE_COOLDOWN_SECONDS


class CooldownTracker:
    def __init__(self) -> None:
        self.shared_cooldowns: dict[int, float] = {}
        self.greeting_uses: dict[int, list[float]] = {}

    def check_shared_cooldown(
        self,
        member: discord.Member,
        now: Optional[float] = None,
    ) -> tuple[bool, float]:
        cooldown_seconds = mute_cooldown_seconds(member)
        if cooldown_seconds <= 0:
            return True, 0.0

        current = time.monotonic() if now is None else now
        until = self.shared_cooldowns.get(member.id, 0.0)
        if until > current:
            return False, until - current

        self.shared_cooldowns[member.id] = current + cooldown_seconds
        return True, 0.0

    def check_greeting_limit(
        self,
        member: discord.Member,
        now: Optional[float] = None,
    ) -> tuple[bool, float]:
        if mute_cooldown_exempt(member):
            return True, 0.0

        current = time.monotonic() if now is None else now
        uses = [
            stamp
            for stamp in self.greeting_uses.get(member.id, [])
            if current - stamp < MUTE_GREETING_WINDOW_SECONDS
        ]
        if len(uses) >= MUTE_GREETING_MAX_USES:
            remaining = MUTE_GREETING_WINDOW_SECONDS - (current - min(uses))
            self.greeting_uses[member.id] = uses
            return False, remaining

        uses.append(current)
        self.greeting_uses[member.id] = uses
        return True, 0.0
