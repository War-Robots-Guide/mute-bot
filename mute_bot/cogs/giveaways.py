from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from mute_bot.config import GIVEAWAY_REACTION
from mute_bot.services.discord_helpers import reply_ephemeral
from mute_bot.services.formatting import parse_duration
from mute_bot.services.permissions import staff_only

if TYPE_CHECKING:
    from mute_bot.bot import MuteBot


class GiveawaysCog(commands.Cog):
    def __init__(self, bot: MuteBot) -> None:
        self.bot = bot

    async def finish_giveaway(self, message_id: int) -> None:
        row = next(
            (
                item
                for item in self.bot.db.active_giveaways()
                if int(item["message_id"]) == message_id
            ),
            None,
        )

        if row is None:
            return

        guild = self.bot.get_guild(int(row["guild_id"]))
        channel = (
            guild.get_channel(int(row["channel_id"]))
            if guild is not None
            else None
        )

        if not isinstance(channel, discord.TextChannel):
            self.bot.db.end_giveaway(message_id)
            return

        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            self.bot.db.end_giveaway(message_id)
            return

        entrants: list[discord.User | discord.Member] = []

        for reaction in message.reactions:
            if str(reaction.emoji) != GIVEAWAY_REACTION:
                continue

            async for user in reaction.users(limit=None):
                if not user.bot:
                    entrants.append(user)
            break

        winner_count = min(int(row["winners"]), len(entrants))
        winners = random.sample(entrants, winner_count) if winner_count else []

        embed = discord.Embed(
            title="Giveaway Ended",
            color=discord.Color.dark_grey(),
            description=(
                f"Prize: {row['prize']}\n"
                + (
                    f"Winners: {', '.join(user.mention for user in winners)}"
                    if winners
                    else "No valid entries."
                )
            ),
        )

        await message.edit(embed=embed)

        if winners:
            await channel.send(
                f"Giveaway ended. Winners: "
                f"{', '.join(user.mention for user in winners)}. "
                f"Prize: {row['prize']}"
            )
        else:
            await channel.send(
                f"Giveaway ended with no valid entries. "
                f"Prize: {row['prize']}"
            )

        self.bot.db.end_giveaway(message_id)
        self.bot.giveaway_tasks.pop(message_id, None)

    async def giveaway_timer(
        self,
        message_id: int,
        ends_at: datetime,
    ) -> None:
        delay = max(
            0.0,
            (ends_at - datetime.now(timezone.utc)).total_seconds(),
        )
        await asyncio.sleep(delay)
        await self.finish_giveaway(message_id)

    async def resume_giveaways(self) -> None:
        for row in self.bot.db.active_giveaways():
            ends_at = datetime.fromisoformat(str(row["ends_at"]))
            message_id = int(row["message_id"])

            self.bot.giveaway_tasks[message_id] = asyncio.create_task(
                self.giveaway_timer(message_id, ends_at)
            )

    @app_commands.command(
        name="giveaway",
        description="Start a giveaway in the current channel.",
    )
    @app_commands.describe(
        duration="Examples: 10m, 2h, 3d, or 1w",
        winners="Number of winners",
        prize="The giveaway prize",
    )
    @staff_only()
    async def giveaway(
        self,
        interaction: discord.Interaction,
        duration: str,
        winners: app_commands.Range[int, 1, 20],
        prize: str,
    ) -> None:
        try:
            delta, _display = parse_duration(duration)
        except ValueError as exc:
            await reply_ephemeral(interaction, str(exc))
            return

        ends_at = datetime.now(timezone.utc) + delta
        unix = int(ends_at.timestamp())

        embed = discord.Embed(
            title="Giveaway",
            color=discord.Color.blurple(),
            description=(
                f"Prize: {prize}\n"
                f"Winners: {winners}\n"
                f"Ends: <t:{unix}:F> (<t:{unix}:R>)\n"
                f"Hosted by: {interaction.user.mention}\n\n"
                f"React with {GIVEAWAY_REACTION} to enter."
            ),
        )

        await interaction.response.send_message(
            "Creating giveaway.",
            ephemeral=True,
        )

        message = await interaction.channel.send(embed=embed)
        await message.add_reaction(GIVEAWAY_REACTION)

        self.bot.db.add_giveaway(
            message.id,
            message.channel.id,
            interaction.user.id,
            prize,
            winners,
            ends_at,
        )

        self.bot.giveaway_tasks[message.id] = asyncio.create_task(
            self.giveaway_timer(message.id, ends_at)
        )

        await interaction.edit_original_response(
            content=f"Giveaway created. Message ID: {message.id}"
        )

    @app_commands.command(
        name="endgiveaway",
        description="End a giveaway immediately.",
    )
    @app_commands.describe(
        message_id="The giveaway message ID",
    )
    @staff_only()
    async def endgiveaway(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ) -> None:
        if not message_id.isdigit():
            await reply_ephemeral(
                interaction,
                "The message ID must contain only digits.",
            )
            return

        numeric_id = int(message_id)

        task = self.bot.giveaway_tasks.pop(numeric_id, None)
        if task is not None:
            task.cancel()

        await interaction.response.defer(ephemeral=True)
        await self.finish_giveaway(numeric_id)
        await interaction.followup.send(
            "Giveaway ended.",
            ephemeral=True,
        )

    @app_commands.command(
        name="rerollgiveaway",
        description="Pick new winner(s) for a giveaway.",
    )
    @app_commands.describe(
        message_id="The giveaway message ID",
        winners="Number of winners",
    )
    @staff_only()
    async def rerollgiveaway(
        self,
        interaction: discord.Interaction,
        message_id: str,
        winners: app_commands.Range[int, 1, 20] = 1,
    ) -> None:
        if not message_id.isdigit():
            await reply_ephemeral(
                interaction,
                "The message ID must contain only digits.",
            )
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await reply_ephemeral(
                interaction,
                "Use this command in the giveaway channel.",
            )
            return

        try:
            message = await interaction.channel.fetch_message(int(message_id))
        except discord.NotFound:
            await reply_ephemeral(
                interaction,
                "Giveaway message not found in this channel.",
            )
            return

        entrants: list[discord.User | discord.Member] = []

        for reaction in message.reactions:
            if str(reaction.emoji) == GIVEAWAY_REACTION:
                async for user in reaction.users(limit=None):
                    if not user.bot:
                        entrants.append(user)
                break

        if not entrants:
            await reply_ephemeral(
                interaction,
                "There are no valid entrants.",
            )
            return

        selected = random.sample(
            entrants,
            min(winners, len(entrants)),
        )

        await interaction.response.send_message(
            f"New winner(s): {', '.join(user.mention for user in selected)}"
        )
