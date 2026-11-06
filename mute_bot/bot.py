from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from mute_bot.cogs import (
    GiveawaysCog,
    InteractionsCog,
    ModerationCog,
    OnboardingCog,
)
from mute_bot.config import DB_PATH, GUILD_ID
from mute_bot.database import Database
from mute_bot.services.discord_helpers import reply_ephemeral

log = logging.getLogger("Mute")


class MuteBot(commands.Bot):
    def __init__(self, db: Optional[Database] = None) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.moderation = True
        intents.messages = True
        intents.message_content = True
        intents.reactions = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=True,
                users=True,
                replied_user=False,
            ),
        )

        self.db = db if db is not None else Database(DB_PATH)
        self.ready_once = False
        self.giveaway_tasks: dict[int, asyncio.Task[None]] = {}
        self.tree.on_error = self.on_app_command_error

    async def register_cogs(self) -> None:
        for cog_cls in (
            ModerationCog,
            InteractionsCog,
            OnboardingCog,
            GiveawaysCog,
        ):
            if self.get_cog(cog_cls.__name__) is None:
                await self.add_cog(cog_cls(self))

    def register_cogs_sync(self) -> None:
        asyncio.run(self.register_cogs())

    async def setup_hook(self) -> None:
        await self.register_cogs()
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.CustomActivity(
                name="Orbital support on standby."
            ),
        )

        if not self.ready_once:
            self.ready_once = True

            onboarding_cog = self.get_cog("OnboardingCog")
            if isinstance(onboarding_cog, OnboardingCog):
                await onboarding_cog.update_member_count()

            giveaways_cog = self.get_cog("GiveawaysCog")
            if isinstance(giveaways_cog, GiveawaysCog):
                await giveaways_cog.resume_giveaways()

        log.info("Logged in as %s", self.user)

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        original = getattr(error, "original", error)

        if isinstance(original, app_commands.CheckFailure):
            await reply_ephemeral(interaction, str(original))
            return

        if isinstance(original, discord.Forbidden):
            await reply_ephemeral(
                interaction,
                "I do not have the required Discord permission or role position.",
            )
            return

        if (
            isinstance(original, discord.NotFound)
            and getattr(original, "code", None) == 10062
        ):
            log.warning(
                "Discord interaction expired before the bot could respond."
            )
            return

        log.exception("Unhandled slash-command error.", exc_info=original)
        try:
            await reply_ephemeral(interaction, "An unexpected error occurred.")
        except discord.NotFound:
            log.warning(
                "Could not send the error response because the interaction expired."
            )

    async def close(self) -> None:
        for task in self.giveaway_tasks.values():
            task.cancel()
        await super().close()
