from datetime import timedelta
import discord
import pytest
from mute_bot.services.formatting import (
    custom_emoji_key,
    format_cooldown_time,
    ordinal,
    parse_duration,
    parse_emoji,
)


def test_format_cooldown_time() -> None:
    assert format_cooldown_time(0.2) == "1s"
    assert format_cooldown_time(59.1) == "1m"
    assert format_cooldown_time(59.0) == "59s"
    assert format_cooldown_time(60) == "1m"
    assert format_cooldown_time(125) == "2m 5s"


def test_ordinal() -> None:
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(3) == "3rd"
    assert ordinal(4) == "4th"
    assert ordinal(11) == "11th"
    assert ordinal(12) == "12th"
    assert ordinal(13) == "13th"
    assert ordinal(21) == "21st"
    assert ordinal(112) == "112th"


def test_parse_duration_valid_and_invalid() -> None:
    delta, label = parse_duration("1h 30m")
    assert delta == timedelta(hours=1, minutes=30)
    assert label == "1 hour, 30 minutes"

    delta_single, label_single = parse_duration("1s")
    assert delta_single == timedelta(seconds=1)
    assert label_single == "1 second"

    for invalid in ("", "10m5x", "0s", "29d", "4w1s", "abc"):
        with pytest.raises(ValueError):
            parse_duration(invalid)


def test_emoji_helpers() -> None:
    assert custom_emoji_key("✅") == "✅"
    assert parse_emoji("✅") == "✅"
    partial = parse_emoji("league_champion:1524798134184837272")
    assert isinstance(partial, discord.PartialEmoji)
    assert partial.name == "league_champion"
    assert partial.id == 1524798134184837272
    assert custom_emoji_key(partial) == "league_champion:1524798134184837272"
