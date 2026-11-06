from __future__ import annotations

import discord
from discord import app_commands

from mute_bot.config import (
    CREDIBLE_SOURCE_ROLE,
    ENLIGHTEN_ROLE_ID,
    EXALTED_FOUR_ROLE,
    WARDEN_ROLE,
)


def staff(member: discord.Member) -> bool:
    role_ids = {role.id for role in member.roles}
    return EXALTED_FOUR_ROLE in role_ids or WARDEN_ROLE in role_ids


def reply_mute_level(member: discord.Member) -> int:
    role_ids = {role.id for role in member.roles}
    if EXALTED_FOUR_ROLE in role_ids:
        return 4
    if WARDEN_ROLE in role_ids:
        return 3
    if CREDIBLE_SOURCE_ROLE in role_ids:
        return 2
    if ENLIGHTEN_ROLE_ID in role_ids:
        return 1
    return 0


def can_moderate(
    moderator: discord.Member,
    target: discord.Member,
) -> tuple[bool, str]:
    guild = moderator.guild

    if moderator.id == target.id:
        return False, "You cannot moderate yourself."
    if target.id == guild.owner_id:
        return False, "The server owner cannot be moderated."
    if staff(target):
        return False, "Staff members cannot be targeted."
    if moderator.id != guild.owner_id and moderator.top_role <= target.top_role:
        return False, "Your role must be above the target's role."
    if guild.me is None or guild.me.top_role <= target.top_role:
        return False, "My role must be above the target's role."

    return True, ""


def staff_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure(
                "This command can only be used in the server."
            )

        if not staff(interaction.user):
            raise app_commands.CheckFailure(
                "You do not have permission to use this command."
            )

        return True

    return app_commands.check(predicate)


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure(
                "This command can only be used in the server."
            )

        if EXALTED_FOUR_ROLE not in {role.id for role in interaction.user.roles}:
            raise app_commands.CheckFailure(
                "Only administrators can use this command."
            )

        return True

    return app_commands.check(predicate)
