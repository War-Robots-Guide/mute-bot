from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from mute_bot.config import (
    ENLIGHTEN_ROLE_CHANCE,
    ENLIGHTEN_ROLE_ID,
    GUILD_ID,
    MODERATION_LOG_CHANNEL,
    TROLL_CHANNEL,
)
from mute_bot.data.responses import (
    CUSTOM_MUTE_PHRASES,
    ENLIGHTEN_RESPONSES,
    PING_ONLY_RESPONSES,
    QUESTION_RESPONSES,
)
from mute_bot.services.automod import attachment_banned_term, find_banned_term
from mute_bot.services.discord_helpers import (
    delete_message,
    reliable_message_reply,
)
from mute_bot.services.formatting import format_cooldown_time
from mute_bot.services.logging_service import modlog, troll_log
from mute_bot.services.mute_chat import (
    CooldownTracker,
    contains_mute_mention,
    is_mute_question,
    is_only_mute_mention,
    normalize_mute_phrase,
)
from mute_bot.services.permissions import reply_mute_level

if TYPE_CHECKING:
    from mute_bot.bot import MuteBot


class InteractionsCog(commands.Cog):
    def __init__(self, bot: MuteBot) -> None:
        self.bot = bot
        self.cooldowns = CooldownTracker()

    async def automatic_unmute_log(
        self,
        guild_id: int,
        user_id: int,
        log_channel_id: int = MODERATION_LOG_CHANNEL,
    ) -> None:
        await asyncio.sleep(10)

        guild = self.bot.get_guild(guild_id)
        if guild is None or self.bot.user is None:
            return

        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        try:
            await member.timeout(
                None,
                reason="Mute duration expired.",
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        if log_channel_id == TROLL_CHANNEL:
            await troll_log(
                self.bot,
                "UNMUTE",
                self.bot.user,
                target=member,
            )
        else:
            await modlog(
                self.bot,
                "UNMUTE",
                member,
                self.bot.user,
                "Mute duration expired.",
                discord.Color.green(),
                channel_id=log_channel_id,
            )

    async def send_channel_cooldown(
        self,
        message: discord.Message,
        seconds: float,
        question: bool,
    ) -> None:
        remaining = max(1, math.ceil(seconds))
        text = (
            f"Ask me again in {remaining} second{'s' if remaining != 1 else ''}."
            if question
            else f"Orbital support will be ready in {remaining} second{'s' if remaining != 1 else ''}."
        )

        try:
            await message.channel.send(
                f"{message.author.mention} {text}",
                delete_after=5,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False,
                    roles=False,
                    users=True,
                    replied_user=False,
                ),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def consume_shared_mute_cooldown(
        self,
        message: discord.Message,
        *,
        question: bool,
    ) -> bool:
        allowed, remaining = self.cooldowns.check_shared_cooldown(message.author)
        if not allowed:
            await delete_message(message)
            await self.send_channel_cooldown(message, remaining, question)
            await troll_log(
                self.bot,
                "COOLDOWN",
                message.author,
                reason="User is still on cooldown.",
                details=f"Remaining: {format_cooldown_time(remaining)}",
            )
            return False
        return True

    async def consume_greeting_limit(self, message: discord.Message) -> bool:
        allowed, remaining = self.cooldowns.check_greeting_limit(message.author)
        if not allowed:
            await delete_message(message)
            await self.send_channel_cooldown(message, remaining, False)
            return False
        return True

    async def handle_custom_mute(self, message: discord.Message) -> bool:
        if not isinstance(message.author, discord.Member):
            return False

        bot_user_id = self.bot.user.id if self.bot.user is not None else None
        if not contains_mute_mention(message, bot_user_id):
            return False

        phrase = normalize_mute_phrase(message.content, bot_user_id)

        if phrase == "enlighten me":
            if not await self.consume_shared_mute_cooldown(message, question=False):
                return True
            guild = message.guild
            role = guild.get_role(ENLIGHTEN_ROLE_ID) if guild is not None else None
            if random.random() < ENLIGHTEN_ROLE_CHANCE and role is not None:
                if role not in message.author.roles:
                    try:
                        await message.author.add_roles(
                            role,
                            reason="Rare @Mute enlighten me reward",
                        )
                    except (discord.Forbidden, discord.HTTPException):
                        await reliable_message_reply(
                            message,
                            random.choice(ENLIGHTEN_RESPONSES),
                        )
                        return True
                await reliable_message_reply(message, "I have enlightened you.")
            else:
                await reliable_message_reply(
                    message,
                    random.choice(ENLIGHTEN_RESPONSES),
                )
            return True

        if is_mute_question(message, bot_user_id):
            if not await self.consume_shared_mute_cooldown(message, question=True):
                return True
            await reliable_message_reply(message, random.choice(QUESTION_RESPONSES))
            return True

        if is_only_mute_mention(message.content, bot_user_id):
            if not await self.consume_shared_mute_cooldown(message, question=False):
                return True
            if not await self.consume_greeting_limit(message):
                return True
            await reliable_message_reply(message, random.choice(PING_ONLY_RESPONSES))
            return True

        if phrase not in CUSTOM_MUTE_PHRASES:
            return True
        if message.reference is None or message.reference.message_id is None:
            return True
        if not await self.consume_shared_mute_cooldown(message, question=False):
            return True

        if isinstance(message.reference.resolved, discord.Message):
            target_message = message.reference.resolved
        else:
            try:
                target_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await reliable_message_reply(
                    message,
                    "🚫 This user has cleanse stacks!",
                )
                return True

        target = target_message.author
        if not isinstance(target, discord.Member):
            await reliable_message_reply(
                message,
                "🚫 This user has cleanse stacks!",
            )
            return True

        author_level = reply_mute_level(message.author)
        target_level = reply_mute_level(target)
        guild = message.guild
        bot_member = guild.me if guild is not None else None

        protected = (
            guild is None
            or target.id == guild.owner_id
            or target.bot
            or message.author.id == target.id
            or author_level < target_level
            or bot_member is None
            or bot_member.top_role <= target.top_role
        )
        if protected:
            await reliable_message_reply(
                message,
                f"🚫 {target.mention} has cleanse stacks!",
            )
            return True

        try:
            await target.timeout(
                datetime.now(timezone.utc) + timedelta(seconds=9),
                reason=f"Reply mute by {message.author} ({message.author.id}): {phrase}",
            )
        except (discord.Forbidden, discord.HTTPException):
            await reliable_message_reply(
                message,
                f"🚫 {target.mention} has cleanse stacks!",
            )
            return True

        await reliable_message_reply(
            message,
            f"✅ {target.mention} has been muted for 9 seconds.",
        )
        await troll_log(
            self.bot,
            "MUTE",
            message.author,
            target=target,
            details="Duration: 9s",
        )
        asyncio.create_task(
            self.automatic_unmute_log(message.guild.id, target.id, TROLL_CHANNEL)
        )
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        if message.author.bot or message.webhook_id is not None:
            return
        if not isinstance(message.author, discord.Member):
            return

        if find_banned_term(message.content):
            await delete_message(message)
            return

        if await attachment_banned_term(message):
            await delete_message(message)
            return

        await self.handle_custom_mute(message)
