from types import SimpleNamespace
from mute_bot.config import EXALTED_FOUR_ROLE, WARDEN_ROLE
from mute_bot.services.mute_chat import (
    CooldownTracker,
    contains_mute_mention,
    is_mute_question,
    is_only_mute_mention,
    normalize_mute_phrase,
)


def _msg(content: str, raw_mentions: list[int] | None = None):
    return SimpleNamespace(content=content, raw_mentions=raw_mentions or [])


def _member(user_id: int, role_ids: list[int] | None = None):
    return SimpleNamespace(
        id=user_id,
        roles=[SimpleNamespace(id=r) for r in (role_ids or [])],
    )


def test_mute_phrase_and_mention_parsing() -> None:
    bot_id = 123456
    assert normalize_mute_phrase("<@!123456> Enlighten Me!!!", bot_id) == "enlighten me"
    assert normalize_mute_phrase("@Mute get him.", bot_id) == "get him"

    assert contains_mute_mention(_msg("hello <@123456>", [bot_id]), bot_id)
    assert contains_mute_mention(_msg("hey @Mute what's up"), bot_id)
    assert not contains_mute_mention(_msg("email me at user@mute.com or @mutes"), bot_id)

    assert is_only_mute_mention("<@123456> ?!.", bot_id)
    assert is_only_mute_mention("@mute", bot_id)
    assert not is_only_mute_mention("@mute hi", bot_id)

    assert is_mute_question(_msg("<@123456> is pathfinder good?", [bot_id]), bot_id)
    assert not is_mute_question(_msg("is pathfinder good?"), bot_id)


def test_cooldown_tracker_enforces_and_exempts_staff() -> None:
    tracker = CooldownTracker()
    normal = _member(10)
    warden = _member(20, [WARDEN_ROLE])
    exalted = _member(30, [EXALTED_FOUR_ROLE])

    allowed, rem = tracker.check_shared_cooldown(normal, now=100.0)
    assert allowed and rem == 0.0

    allowed2, rem2 = tracker.check_shared_cooldown(normal, now=150.0)
    assert not allowed2 and rem2 == 130.0

    allowed3, _ = tracker.check_shared_cooldown(normal, now=281.0)
    assert allowed3

    # Both staff roles are always exempt from shared cooldown and greeting limits
    for staff_member in (warden, exalted):
        assert tracker.check_shared_cooldown(staff_member, now=100.0) == (True, 0.0)
        assert tracker.check_shared_cooldown(staff_member, now=101.0) == (True, 0.0)
        for offset in range(5):
            assert tracker.check_greeting_limit(staff_member, now=100.0 + offset) == (True, 0.0)


def test_greeting_rate_limit_window() -> None:
    tracker = CooldownTracker()
    normal = _member(10)

    assert tracker.check_greeting_limit(normal, now=10.0) == (True, 0.0)
    assert tracker.check_greeting_limit(normal, now=20.0) == (True, 0.0)
    allowed, rem = tracker.check_greeting_limit(normal, now=25.0)
    assert not allowed and rem == 15.0

    # After the 30s window from first use expires
    assert tracker.check_greeting_limit(normal, now=41.0) == (True, 0.0)
