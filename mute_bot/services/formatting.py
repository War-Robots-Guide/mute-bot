from __future__ import annotations

import math
import re
from datetime import timedelta

import discord


def format_cooldown_time(seconds: float) -> str:
    remaining = max(1, math.ceil(seconds))
    minutes, secs = divmod(remaining, 60)
    if minutes and secs:
        return f"{minutes}m {secs}s"
    if minutes:
        return f"{minutes}m"
    return f"{secs}s"


def identity(user: discord.abc.User) -> str:
    username = getattr(user, "name", str(user))
    return f"{username} ({user.id})"


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def parse_duration(text: str) -> tuple[timedelta, str]:
    compact = re.sub(r"\s+", "", text.lower())
    matches = re.findall(r"(\d+)([smhdw])", compact)

    if not matches or "".join(number + unit for number, unit in matches) != compact:
        raise ValueError("Use a duration such as 30s, 10m, 2h, 3d, or 1w.")

    units = {
        "s": (1, "second"),
        "m": (60, "minute"),
        "h": (3600, "hour"),
        "d": (86400, "day"),
        "w": (604800, "week"),
    }

    total_seconds = 0
    labels: list[str] = []

    for raw_number, unit in matches:
        number = int(raw_number)
        multiplier, name = units[unit]
        total_seconds += number * multiplier
        labels.append(f"{number} {name}{'' if number == 1 else 's'}")

    if total_seconds <= 0 or total_seconds > 28 * 86400:
        raise ValueError("The duration must be between 1 second and 28 days.")

    return timedelta(seconds=total_seconds), ", ".join(labels)


def custom_emoji_key(emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
    if isinstance(emoji, str):
        return emoji
    if emoji.id is None:
        return emoji.name
    return f"{emoji.name}:{emoji.id}"


def parse_emoji(value: str) -> str | discord.PartialEmoji:
    if ":" not in value:
        return value
    name, raw_id = value.rsplit(":", 1)
    return discord.PartialEmoji(name=name, id=int(raw_id))
