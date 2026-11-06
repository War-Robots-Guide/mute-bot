from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands

from mute_bot.config import (
    AUTOMOD_LOG_CHANNEL_ID,
    MODERATION_LOG_CHANNEL,
    TROLL_CHANNEL,
)
from mute_bot.services.discord_helpers import send_embed
from mute_bot.services.formatting import identity


async def modlog(
    bot: commands.Bot,
    action: str,
    target: discord.abc.User,
    moderator: discord.abc.User,
    reason: str,
    color: discord.Color,
    details: Optional[str] = None,
    channel_id: int = MODERATION_LOG_CHANNEL,
) -> None:
    embed = discord.Embed(
        title=f"Moderation Log: {action}",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Target", value=identity(target), inline=False)
    embed.add_field(name="Moderator", value=identity(moderator), inline=False)
    embed.add_field(name="Reason", value=reason[:1024], inline=False)

    if details:
        embed.add_field(name="Details", value=details[:1024], inline=False)

    await send_embed(bot, channel_id, embed)


async def troll_log(
    bot: commands.Bot,
    action: str,
    user: discord.abc.User,
    *,
    target: Optional[discord.abc.User] = None,
    reason: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    embed = discord.Embed(
        title=f"Troll Log: {action}",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="User", value=identity(user), inline=False)

    if target is not None:
        embed.add_field(name="Target", value=identity(target), inline=False)

    if reason:
        embed.add_field(name="Reason", value=reason[:1024], inline=False)

    if details:
        embed.add_field(name="Details", value=details[:1024], inline=False)

    await send_embed(bot, TROLL_CHANNEL, embed)


async def automod_log(
    bot: commands.Bot,
    member: discord.Member,
    channel: discord.abc.GuildChannel | discord.Thread,
    reason: str,
    content: str,
) -> None:
    if not AUTOMOD_LOG_CHANNEL_ID:
        return

    embed = discord.Embed(
        title="Automatic Moderation Log",
        color=discord.Color.dark_orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="User", value=identity(member), inline=False)
    embed.add_field(
        name="Channel",
        value=f"{channel.mention} (ID: {channel.id})",
        inline=False,
    )
    embed.add_field(name="Reason", value=reason[:1024], inline=False)

    if content:
        embed.add_field(name="Content", value=content[:1024], inline=False)

    await send_embed(bot, AUTOMOD_LOG_CHANNEL_ID, embed)
