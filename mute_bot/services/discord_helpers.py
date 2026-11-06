from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands

log = logging.getLogger("Mute")


async def reliable_message_reply(message: discord.Message, content: str) -> None:
    for attempt in range(3):
        try:
            await message.reply(content, mention_author=False)
            return
        except discord.HTTPException:
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))

    try:
        await message.channel.send(
            content,
            reference=message,
            mention_author=False,
        )
    except discord.HTTPException:
        log.exception("Could not reply to message %s.", message.id)


async def reply_ephemeral(
    interaction: discord.Interaction,
    content: str,
) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)


async def delete_message(message: discord.Message) -> bool:
    try:
        await asyncio.sleep(0.4)
        await message.delete()
        return True
    except (discord.NotFound, discord.Forbidden):
        return False
    except discord.HTTPException:
        log.exception("Could not delete message %s.", message.id)
        return False


async def get_text_channel(
    bot: commands.Bot,
    channel_id: int,
) -> Optional[discord.TextChannel]:
    if not channel_id:
        return None

    existing = bot.get_channel(channel_id)
    if isinstance(existing, discord.TextChannel):
        return existing

    try:
        fetched = await bot.fetch_channel(channel_id)
        return fetched if isinstance(fetched, discord.TextChannel) else None
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def send_embed(
    bot: commands.Bot,
    channel_id: int,
    embed: discord.Embed,
) -> None:
    channel = await get_text_channel(bot, channel_id)
    if channel is None:
        return

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        log.exception("Could not send embed to channel %s.", channel_id)


def resolve_configured_role(
    guild: discord.Guild,
    role_id: int,
    role_name: str,
) -> Optional[discord.Role]:
    if role_id:
        role = guild.get_role(role_id)
        if role is not None:
            return role

    wanted = role_name.casefold().strip()
    for role in guild.roles:
        if role.name.casefold().strip() == wanted:
            return role
    return None
