from types import SimpleNamespace
from mute_bot.config import (
    CREDIBLE_SOURCE_ROLE,
    ENLIGHTEN_ROLE_ID,
    EXALTED_FOUR_ROLE,
    WARDEN_ROLE,
)
from mute_bot.services.permissions import can_moderate, reply_mute_level, staff


def _make_member(member_id: int, role_ids: list[int], top_role_pos: int = 1, guild=None):
    roles = [SimpleNamespace(id=rid) for rid in role_ids]
    return SimpleNamespace(
        id=member_id,
        roles=roles,
        top_role=top_role_pos,
        guild=guild,
    )


def test_staff_and_reply_mute_levels() -> None:
    assert staff(_make_member(1, [EXALTED_FOUR_ROLE]))
    assert staff(_make_member(2, [WARDEN_ROLE]))
    assert not staff(_make_member(3, [CREDIBLE_SOURCE_ROLE]))

    assert reply_mute_level(_make_member(1, [EXALTED_FOUR_ROLE])) == 4
    assert reply_mute_level(_make_member(2, [WARDEN_ROLE])) == 3
    assert reply_mute_level(_make_member(3, [CREDIBLE_SOURCE_ROLE])) == 2
    assert reply_mute_level(_make_member(4, [ENLIGHTEN_ROLE_ID])) == 1
    assert reply_mute_level(_make_member(5, [])) == 0


def test_can_moderate_hierarchy_and_protections() -> None:
    guild = SimpleNamespace(owner_id=999, me=SimpleNamespace(top_role=50))
    mod = _make_member(10, [WARDEN_ROLE], top_role_pos=30, guild=guild)
    regular = _make_member(20, [], top_role_pos=5, guild=guild)
    other_staff = _make_member(30, [WARDEN_ROLE], top_role_pos=10, guild=guild)
    owner = _make_member(999, [], top_role_pos=100, guild=guild)
    higher_role_user = _make_member(40, [], top_role_pos=40, guild=guild)
    above_bot_user = _make_member(50, [], top_role_pos=60, guild=guild)
    admin_owner = _make_member(999, [EXALTED_FOUR_ROLE], top_role_pos=100, guild=guild)

    assert can_moderate(mod, regular) == (True, "")
    assert can_moderate(mod, mod) == (False, "You cannot moderate yourself.")
    assert can_moderate(mod, owner) == (False, "The server owner cannot be moderated.")
    assert can_moderate(admin_owner, other_staff) == (False, "Staff members cannot be targeted.")
    assert can_moderate(mod, higher_role_user) == (False, "Your role must be above the target's role.")
    assert can_moderate(admin_owner, above_bot_user) == (False, "My role must be above the target's role.")
