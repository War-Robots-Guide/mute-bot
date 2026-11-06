from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from mute_bot.config import (
    DELETE_LOG_CHANNEL_ID,
    EDIT_LOG_CHANNEL_ID,
    GUILD_ID,
)
from mute_bot.services.discord_helpers import reply_ephemeral, send_embed
from mute_bot.services.formatting import identity, parse_duration
from mute_bot.services.logging_service import modlog
from mute_bot.services.permissions import can_moderate, staff_only

if TYPE_CHECKING:
    from mute_bot.bot import MuteBot


class ModerationCog(commands.Cog):
    def __init__(self, bot: MuteBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        if (
            before.guild is None
            or before.guild.id != GUILD_ID
            or before.author.bot
            or before.content == after.content
            or not EDIT_LOG_CHANNEL_ID
        ):
            return

        embed = discord.Embed(
            title="Edited Message",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Author", value=identity(before.author), inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(
            name="Before",
            value=(before.content or "No text")[:1024],
            inline=False,
        )
        embed.add_field(
            name="After",
            value=(after.content or "No text")[:1024],
            inline=False,
        )
        embed.add_field(name="Message", value=after.jump_url, inline=False)

        await send_embed(self.bot, EDIT_LOG_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if (
            message.guild is None
            or message.guild.id != GUILD_ID
            or message.author.bot
            or not DELETE_LOG_CHANNEL_ID
        ):
            return

        embed = discord.Embed(
            title="Deleted Message",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Author", value=identity(message.author), inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(
            name="Content",
            value=(message.content or "No text")[:1024],
            inline=False,
        )

        if message.attachments:
            names = "\n".join(item.filename for item in message.attachments)
            embed.add_field(name="Attachments", value=names[:1024], inline=False)

        await send_embed(self.bot, DELETE_LOG_CHANNEL_ID, embed)

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member="The member to ban",
        reason="The required reason for the ban",
        delete_message_days="Message history to delete, from 0 to 7 days",
    )
    @staff_only()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        allowed, error = can_moderate(interaction.user, member)

        if not allowed:
            await reply_ephemeral(interaction, error)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await interaction.guild.ban(
                member,
                reason=f"{reason} | Moderator: {interaction.user}",
                delete_message_seconds=delete_message_days * 86400,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "I cannot ban that member.",
                ephemeral=True,
            )
            return

        await modlog(
            self.bot,
            "BAN",
            member,
            interaction.user,
            reason,
            discord.Color.red(),
            f"Deleted message history: {delete_message_days} day(s)",
        )

        await interaction.followup.send(
            f"Banned {member}.",
            ephemeral=True,
        )

    @app_commands.command(name="mute", description="Mute a member for a duration.")
    @app_commands.describe(
        member="The member to mute",
        duration="Examples: 30s, 10m, 2h, 3d, or 1w",
        reason="The required reason for the mute",
    )
    @staff_only()
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str,
    ) -> None:
        allowed, error = can_moderate(interaction.user, member)

        if not allowed:
            await reply_ephemeral(interaction, error)
            return

        try:
            delta, display = parse_duration(duration)
        except ValueError as exc:
            await reply_ephemeral(interaction, str(exc))
            return

        await member.timeout(
            datetime.now(timezone.utc) + delta,
            reason=f"{reason} | Moderator: {interaction.user}",
        )

        await modlog(
            self.bot,
            "MUTE",
            member,
            interaction.user,
            reason,
            discord.Color.orange(),
            f"Duration: {display}",
        )

        await interaction.response.send_message(
            f"Muted {member} for {display}.",
            ephemeral=True,
        )

    @app_commands.command(name="unmute", description="Remove a member's timeout.")
    @app_commands.describe(
        member="The member to unmute",
        reason="The reason for removing the mute",
    )
    @staff_only()
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Manual unmute.",
    ) -> None:
        allowed, error = can_moderate(interaction.user, member)

        if not allowed:
            await reply_ephemeral(interaction, error)
            return

        await member.timeout(
            None,
            reason=f"{reason} | Moderator: {interaction.user}",
        )

        await modlog(
            self.bot,
            "UNMUTE",
            member,
            interaction.user,
            reason,
            discord.Color.green(),
        )

        await interaction.response.send_message(
            f"Unmuted {member}.",
            ephemeral=True,
        )

    @app_commands.command(name="warn", description="Add a warning to a member.")
    @app_commands.describe(
        member="The member to warn",
        reason="The required reason for the warning",
    )
    @staff_only()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        allowed, error = can_moderate(interaction.user, member)

        if not allowed:
            await reply_ephemeral(interaction, error)
            return

        warning_id = self.bot.db.add_warning(
            member.id,
            interaction.user.id,
            reason,
        )

        try:
            await member.send(
                f"You received a warning in {interaction.guild.name}.\n\n"
                f"Reason:\n{reason}"
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        await modlog(
            self.bot,
            "WARN",
            member,
            interaction.user,
            reason,
            discord.Color.yellow(),
            f"Warning ID: {warning_id}",
        )

        await interaction.response.send_message(
            f"Warned {member}.",
            ephemeral=True,
        )

    @app_commands.command(name="warnings", description="Show a member's warnings.")
    @app_commands.describe(
        member="The member whose warnings should be shown",
    )
    @staff_only()
    async def warnings_command(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        rows = self.bot.db.warnings(member.id)

        if not rows:
            await interaction.response.send_message(
                f"{member} has no warnings.",
                ephemeral=True,
            )
            return

        text = "\n\n".join(
            (
                f"ID {row['id']} | Moderator ID {row['moderator_id']} | "
                f"{row['created_at']}\n{row['reason']}"
            )
            for row in rows
        )

        if len(text) <= 1900:
            await interaction.response.send_message(
                f"Warnings for {member}:\n\n{text}",
                ephemeral=True,
            )
        else:
            file = discord.File(
                io.BytesIO(text.encode("utf-8")),
                filename=f"warnings_{member.id}.txt",
            )
            await interaction.response.send_message(
                file=file,
                ephemeral=True,
            )

    @app_commands.command(
        name="clearwarnings",
        description="Delete all warnings for a member.",
    )
    @app_commands.describe(
        member="The member whose warnings should be deleted",
        reason="The required reason for clearing warnings",
    )
    @staff_only()
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        count = self.bot.db.clear_warnings(member.id)

        await modlog(
            self.bot,
            "CLEAR WARNINGS",
            member,
            interaction.user,
            reason,
            discord.Color.yellow(),
            f"Deleted warnings: {count}",
        )

        await interaction.response.send_message(
            f"Cleared {count} warning(s) for {member}.",
            ephemeral=True,
        )
