from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from mute_bot.config import (
    AUTO_CREATE_MEMBER_COUNT_CHANNEL,
    BOOSTER_RULES_CHANNEL,
    BOOSTER_RULES_MESSAGE,
    BULLETIN_CHANNEL,
    BULLETIN_MESSAGE,
    CHECKMARK,
    GUILD_ID,
    LEAGUE_MESSAGE,
    LEAGUE_ROLE_NAMES,
    LEAGUE_ROLES,
    MEMBER_COUNT_CHANNEL_ID,
    MEMBER_COUNT_CHANNEL_NAME,
    MEMBER_COUNT_EDIT_INTERVAL,
    NOTIFICATION_MESSAGE,
    NOTIFICATION_ROLES,
    PLATFORM_MESSAGE,
    PLATFORM_ROLES,
    ROLE_SELECTION_CHANNEL,
    RULES_CHANNEL,
    RULES_MESSAGE,
    WELCOME_CHANNEL_ID,
)
from mute_bot.services.discord_helpers import (
    get_text_channel,
    resolve_configured_role,
)
from mute_bot.services.formatting import (
    custom_emoji_key,
    ordinal,
    parse_emoji,
)
from mute_bot.services.permissions import staff_only

if TYPE_CHECKING:
    from mute_bot.bot import MuteBot

log = logging.getLogger("Mute")


def reaction_removal_key(
    user_id: int,
    channel_id: int,
    message_id: int,
    emoji: discord.PartialEmoji | discord.Emoji | str,
) -> tuple[int, int, int, str]:
    return (
        user_id,
        channel_id,
        message_id,
        custom_emoji_key(emoji),
    )


def locked_reaction_message(payload: discord.RawReactionActionEvent) -> bool:
    return (payload.channel_id, payload.message_id) in {
        (RULES_CHANNEL, RULES_MESSAGE),
        (BOOSTER_RULES_CHANNEL, BOOSTER_RULES_MESSAGE),
        (BULLETIN_CHANNEL, BULLETIN_MESSAGE),
    }


def onboarding_dm_text(member: discord.Member) -> str:
    return "\n".join(
        [
            f"Welcome to {member.guild.name}.",
            "",
            "Please read the following channels carefully before getting started:",
            f"<#{RULES_CHANNEL}>",
            f"<#{BULLETIN_CHANNEL}>",
            "",
            "Once you have read them, please get your roles here:",
            f"<#{ROLE_SELECTION_CHANNEL}>",
            "",
            "Make sure to choose the roles that apply to you.",
        ]
    )


class OnboardingCog(commands.Cog):
    def __init__(self, bot: MuteBot) -> None:
        self.bot = bot
        self.reaction_member_locks: dict[int, asyncio.Lock] = {}
        self.bot_managed_reaction_removals: set[tuple[int, int, int, str]] = set()
        self._member_count_edit_lock = asyncio.Lock()
        self._member_count_last_edit = 0.0
        self._member_count_pending_task: Optional[asyncio.Task[None]] = None

    def reaction_member_lock(self, user_id: int) -> asyncio.Lock:
        lock = self.reaction_member_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self.reaction_member_locks[user_id] = lock
        return lock

    def league_message_id(self) -> int:
        saved = self.bot.db.setting("league_message")
        if saved and saved.isdigit():
            return int(saved)
        return LEAGUE_MESSAGE

    def notification_message_id(self) -> int:
        saved = self.bot.db.setting("notification_message")
        if saved and saved.isdigit():
            return int(saved)
        return NOTIFICATION_MESSAGE

    def onboarding_state(self, member: discord.Member) -> bool:
        row = self.bot.db.onboarding(member.id)
        return (
            bool(row["rules"])
            and bool(row["booster_rules"])
            and bool(row["bulletin"])
            and bool(row["role_selected"])
            and bool(row["platform_selected"])
        )

    async def apply_onboarding_access(self, member: discord.Member) -> None:
        if member.bot:
            return

        complete = self.onboarding_state(member)
        self.bot.db.set_onboarding(member.id, "completed", int(complete))
        if complete:
            self.bot.db.set_onboarding(member.id, "ever_verified", 1)
        self.bot.db.set_onboarding(member.id, "exempt", 0)

    async def update_onboarding_dm(self, member: discord.Member) -> None:
        row = self.bot.db.onboarding(member.id)
        if row["dm_message_id"]:
            return

        try:
            sent = await member.send(onboarding_dm_text(member))
            self.bot.db.set_onboarding(member.id, "dm_channel_id", sent.channel.id)
            self.bot.db.set_onboarding(member.id, "dm_message_id", sent.id)
        except discord.Forbidden:
            return
        except discord.HTTPException as exc:
            if exc.code == 40003:
                log.warning(
                    "Discord temporarily blocked opening a DM for %s; onboarding continues normally.",
                    member.id,
                )
                return
            log.exception("Could not send onboarding DM for %s.", member.id)

    async def send_welcome(self, member: discord.Member) -> None:
        channel: Optional[discord.TextChannel] = None

        if WELCOME_CHANNEL_ID:
            channel = await get_text_channel(self.bot, WELCOME_CHANNEL_ID)

        if channel is None:
            channel = member.guild.system_channel

        if channel is None:
            log.warning(
                "No welcome channel is configured and the server has no system channel."
            )
            return

        count = member.guild.member_count or len(member.guild.members)
        text = (
            f"Hello, {member.display_name}, welcome to War Robots Guide.\n"
            f"You are the {ordinal(count)} member to join."
        )

        try:
            await channel.send(text)
        except discord.HTTPException:
            log.exception("Could not send welcome message.")

    async def find_or_create_member_count_channel(
        self,
        guild: discord.Guild,
    ) -> Optional[discord.abc.GuildChannel]:
        if MEMBER_COUNT_CHANNEL_ID:
            existing = guild.get_channel(MEMBER_COUNT_CHANNEL_ID)
            if existing is not None:
                return existing

        saved_id = self.bot.db.setting("member_count_channel_id")
        if saved_id and saved_id.isdigit():
            saved = guild.get_channel(int(saved_id))
            if saved is not None:
                return saved

        for channel in guild.channels:
            if channel.name.lower().startswith("members:"):
                self.bot.db.set_setting("member_count_channel_id", str(channel.id))
                return channel

        if not AUTO_CREATE_MEMBER_COUNT_CHANNEL:
            return None

        try:
            channel = await guild.create_voice_channel(
                name=MEMBER_COUNT_CHANNEL_NAME.format(
                    count=guild.member_count or len(guild.members)
                ),
                reason="Automatic member count channel",
            )
            self.bot.db.set_setting("member_count_channel_id", str(channel.id))
            return channel
        except discord.Forbidden:
            log.warning("Missing Manage Channels permission for member count.")
        except discord.HTTPException:
            log.exception("Could not create the member count channel.")

        return None

    async def _perform_member_count_update(self) -> None:
        async with self._member_count_edit_lock:
            guild = self.bot.get_guild(GUILD_ID)
            if guild is None:
                return

            count = guild.member_count or len(guild.members)
            channel = await self.find_or_create_member_count_channel(guild)
            if channel is None:
                return

            new_name = MEMBER_COUNT_CHANNEL_NAME.format(count=count)
            if channel.name == new_name:
                return

            elapsed = time.monotonic() - self._member_count_last_edit
            if self._member_count_last_edit and elapsed < MEMBER_COUNT_EDIT_INTERVAL:
                await asyncio.sleep(MEMBER_COUNT_EDIT_INTERVAL - elapsed)

                guild = self.bot.get_guild(GUILD_ID)
                if guild is None:
                    return
                count = guild.member_count or len(guild.members)
                channel = await self.find_or_create_member_count_channel(guild)
                if channel is None:
                    return
                new_name = MEMBER_COUNT_CHANNEL_NAME.format(count=count)
                if channel.name == new_name:
                    return

            try:
                await channel.edit(
                    name=new_name,
                    reason="Automatic member count update",
                )
                self._member_count_last_edit = time.monotonic()
            except discord.Forbidden:
                log.warning("Missing Manage Channels permission for member count.")
            except discord.HTTPException:
                log.exception("Could not update member count channel.")

    async def _member_count_update_runner(self) -> None:
        try:
            await self._perform_member_count_update()
        finally:
            self._member_count_pending_task = None

    async def update_member_count(self) -> None:
        if (
            self._member_count_pending_task is None
            or self._member_count_pending_task.done()
        ):
            self._member_count_pending_task = asyncio.create_task(
                self._member_count_update_runner()
            )

    async def payload_member(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> Optional[discord.Member]:
        guild = self.bot.get_guild(payload.guild_id or 0)
        if guild is None:
            return None

        if isinstance(payload.member, discord.Member):
            return payload.member

        member = guild.get_member(payload.user_id)
        if member is not None:
            return member

        try:
            return await guild.fetch_member(payload.user_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def fetch_required_message(
        self,
        guild: discord.Guild,
        channel_id: int,
        message_id: int,
    ) -> Optional[discord.Message]:
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            log.error("Required onboarding channel %s is unavailable.", channel_id)
            return None

        for attempt in range(3):
            try:
                return await channel.fetch_message(message_id)
            except (discord.NotFound, discord.Forbidden):
                log.error(
                    "Required onboarding message %s in channel %s is unavailable.",
                    message_id,
                    channel_id,
                )
                return None
            except discord.HTTPException:
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))

        log.error(
            "Discord did not return onboarding message %s in channel %s after retries.",
            message_id,
            channel_id,
        )
        return None

    async def reaction_user_ids(
        self,
        message: discord.Message,
        emoji_key: str,
    ) -> Optional[set[int]]:
        matching_reaction = next(
            (
                reaction
                for reaction in message.reactions
                if custom_emoji_key(reaction.emoji) == emoji_key
                or str(reaction.emoji) == emoji_key
                or getattr(reaction.emoji, "name", None) == emoji_key
            ),
            None,
        )

        if matching_reaction is None:
            return set()

        for attempt in range(3):
            try:
                return {
                    user.id
                    async for user in matching_reaction.users(limit=None)
                    if not user.bot
                }
            except discord.HTTPException:
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))

        log.warning(
            "Could not read reaction users for message %s and emoji %s.",
            message.id,
            emoji_key,
        )
        return None

    async def message_has_member_reaction(
        self,
        guild: discord.Guild,
        channel_id: int,
        message_id: int,
        emoji_key: str,
        user_id: int,
    ) -> Optional[bool]:
        message = await self.fetch_required_message(guild, channel_id, message_id)
        if message is None:
            return None

        users = await self.reaction_user_ids(message, emoji_key)
        if users is None:
            return None
        return user_id in users

    async def refresh_member_required_confirmations(
        self,
        member: discord.Member,
    ) -> None:
        checks = (
            ("rules", RULES_CHANNEL, RULES_MESSAGE),
            ("booster_rules", BOOSTER_RULES_CHANNEL, BOOSTER_RULES_MESSAGE),
            ("bulletin", BULLETIN_CHANNEL, BULLETIN_MESSAGE),
        )

        for field, channel_id, message_id in checks:
            result = await self.message_has_member_reaction(
                member.guild,
                channel_id,
                message_id,
                CHECKMARK,
                member.id,
            )
            if result is True:
                self.bot.db.set_onboarding(member.id, field, 1)

    async def handle_verification_reaction(
        self,
        payload: discord.RawReactionActionEvent,
        added: bool,
    ) -> bool:
        if payload.guild_id != GUILD_ID or str(payload.emoji) != CHECKMARK:
            return False

        mapping = {
            (RULES_CHANNEL, RULES_MESSAGE): "rules",
            (BOOSTER_RULES_CHANNEL, BOOSTER_RULES_MESSAGE): "booster_rules",
            (BULLETIN_CHANNEL, BULLETIN_MESSAGE): "bulletin",
        }

        field = mapping.get((payload.channel_id, payload.message_id))
        if field is None:
            return False

        member = await self.payload_member(payload)
        if member is None or member.bot:
            return True

        self.bot.db.ensure_user(member.id)

        if not added:
            return True

        self.bot.db.set_onboarding(member.id, "exempt", 0)
        self.bot.db.set_onboarding(member.id, field, 1)

        await self.refresh_member_required_confirmations(member)
        await self.apply_onboarding_access(member)
        return True

    async def complete_role_selection_if_needed(
        self,
        member: discord.Member,
        added: bool,
    ) -> None:
        if not added or not self.bot.db.has_onboarding(member.id):
            return
        self.bot.db.set_onboarding(member.id, "role_selected", 1)
        await self.apply_onboarding_access(member)

    async def handle_reaction_roles(
        self,
        payload: discord.RawReactionActionEvent,
        added: bool,
    ) -> bool:
        if payload.guild_id != GUILD_ID:
            return False

        emoji_key = custom_emoji_key(payload.emoji)

        if payload.channel_id == ROLE_SELECTION_CHANNEL and payload.message_id in {
            LEAGUE_MESSAGE,
            self.league_message_id(),
        }:
            if emoji_key not in LEAGUE_ROLES:
                return True
            role_id = LEAGUE_ROLES[emoji_key]

            member = await self.payload_member(payload)
            guild = self.bot.get_guild(GUILD_ID)

            if member is None or guild is None or member.bot:
                return True

            selected_role = resolve_configured_role(
                guild,
                role_id,
                LEAGUE_ROLE_NAMES.get(emoji_key, ""),
            )
            if selected_role is None:
                log.warning("League role could not be resolved for emoji %s.", emoji_key)
                return True

            try:
                if added:
                    other_roles = {
                        resolved.id
                        for configured_emoji, configured_id in LEAGUE_ROLES.items()
                        if configured_emoji != emoji_key
                        for resolved in [
                            resolve_configured_role(
                                guild,
                                configured_id,
                                LEAGUE_ROLE_NAMES.get(configured_emoji, ""),
                            )
                        ]
                        if resolved is not None
                    }

                    remove_roles = [
                        role for role in member.roles if role.id in other_roles
                    ]

                    if remove_roles:
                        await member.remove_roles(
                            *remove_roles,
                            reason="League role changed",
                        )

                    if selected_role not in member.roles:
                        await member.add_roles(
                            selected_role,
                            reason="League role selected",
                        )

                    await self.complete_role_selection_if_needed(member, True)

                    channel = self.bot.get_channel(payload.channel_id)
                    if isinstance(channel, discord.TextChannel):
                        try:
                            panel = await channel.fetch_message(payload.message_id)
                            for configured_emoji in LEAGUE_ROLES:
                                if configured_emoji == emoji_key:
                                    continue
                                try:
                                    removal_emoji = parse_emoji(configured_emoji)
                                    self.bot_managed_reaction_removals.add(
                                        reaction_removal_key(
                                            member.id,
                                            panel.channel.id,
                                            panel.id,
                                            removal_emoji,
                                        )
                                    )
                                    await panel.remove_reaction(
                                        removal_emoji,
                                        member,
                                    )
                                except (
                                    discord.NotFound,
                                    discord.Forbidden,
                                    discord.HTTPException,
                                ):
                                    pass
                        except (
                            discord.NotFound,
                            discord.Forbidden,
                            discord.HTTPException,
                        ):
                            pass

                elif selected_role in member.roles:
                    await member.remove_roles(
                        selected_role,
                        reason="League role removed",
                    )

                    if self.bot.db.has_onboarding(member.id):
                        row = self.bot.db.onboarding(member.id)
                        if not bool(row["exempt"]):
                            remaining_league = any(
                                resolve_configured_role(
                                    guild,
                                    configured_id,
                                    LEAGUE_ROLE_NAMES.get(configured_emoji, ""),
                                )
                                in member.roles
                                for configured_emoji, configured_id in LEAGUE_ROLES.items()
                            )
                            if not remaining_league:
                                self.bot.db.set_onboarding(
                                    member.id, "role_selected", 0
                                )
                                self.bot.db.set_onboarding(member.id, "completed", 0)
                                await self.apply_onboarding_access(member)

            except discord.Forbidden:
                log.warning("Could not update league role for %s.", member.id)
            except discord.HTTPException:
                log.exception("Could not update league role for %s.", member.id)

            return True

        if (
            payload.channel_id == ROLE_SELECTION_CHANNEL
            and payload.message_id == PLATFORM_MESSAGE
        ):
            emoji_name = getattr(payload.emoji, "name", str(payload.emoji))
            platform_key = next(
                (
                    configured_name
                    for configured_name in PLATFORM_ROLES
                    if configured_name.casefold() == emoji_name.casefold()
                ),
                None,
            )
            if platform_key is None:
                return True
            emoji_name = platform_key
            role_id = PLATFORM_ROLES[emoji_name]

            member = await self.payload_member(payload)
            guild = self.bot.get_guild(GUILD_ID)
            if member is None or guild is None or member.bot:
                return True

            selected_role = guild.get_role(role_id)
            if selected_role is None:
                log.warning("Platform role could not be resolved: %s.", role_id)
                return True

            try:
                if added:
                    other_role_ids = {
                        configured_role_id
                        for configured_name, configured_role_id in PLATFORM_ROLES.items()
                        if configured_name != emoji_name
                    }
                    remove_roles = [
                        role
                        for role in member.roles
                        if role.id in other_role_ids
                    ]

                    if remove_roles:
                        await member.remove_roles(
                            *remove_roles,
                            reason="Platform role changed",
                        )

                    if selected_role not in member.roles:
                        await member.add_roles(
                            selected_role,
                            reason="Platform role selected",
                        )

                    self.bot.db.ensure_user(member.id)
                    self.bot.db.set_onboarding(member.id, "platform_selected", 1)
                    await self.apply_onboarding_access(member)

                    channel = self.bot.get_channel(payload.channel_id)
                    if isinstance(channel, discord.TextChannel):
                        try:
                            panel = await channel.fetch_message(payload.message_id)

                            selected_emoji_id = getattr(payload.emoji, "id", None)
                            selected_emoji_name = getattr(
                                payload.emoji,
                                "name",
                                str(payload.emoji),
                            ).casefold()

                            for reaction in panel.reactions:
                                reaction_id = getattr(reaction.emoji, "id", None)
                                reaction_name = getattr(
                                    reaction.emoji,
                                    "name",
                                    str(reaction.emoji),
                                ).casefold()

                                is_selected = (
                                    selected_emoji_id is not None
                                    and reaction_id == selected_emoji_id
                                ) or (
                                    selected_emoji_id is None
                                    and reaction_name == selected_emoji_name
                                )

                                if is_selected:
                                    continue

                                try:
                                    users = {
                                        user.id
                                        async for user in reaction.users(limit=None)
                                    }
                                except discord.HTTPException:
                                    continue

                                if member.id not in users:
                                    continue

                                self.bot_managed_reaction_removals.add(
                                    reaction_removal_key(
                                        member.id,
                                        panel.channel.id,
                                        panel.id,
                                        reaction.emoji,
                                    )
                                )

                                try:
                                    await panel.remove_reaction(
                                        reaction.emoji,
                                        member,
                                    )
                                except (
                                    discord.NotFound,
                                    discord.Forbidden,
                                    discord.HTTPException,
                                ):
                                    self.bot_managed_reaction_removals.discard(
                                        reaction_removal_key(
                                            member.id,
                                            panel.channel.id,
                                            panel.id,
                                            reaction.emoji,
                                        )
                                    )
                        except (
                            discord.NotFound,
                            discord.Forbidden,
                            discord.HTTPException,
                        ):
                            pass

                elif selected_role in member.roles:
                    await member.remove_roles(
                        selected_role,
                        reason="Platform role removed",
                    )

                    remaining_platform = any(
                        role.id in set(PLATFORM_ROLES.values())
                        for role in member.roles
                        if role.id != selected_role.id
                    )
                    if not remaining_platform:
                        self.bot.db.ensure_user(member.id)
                        self.bot.db.set_onboarding(member.id, "platform_selected", 0)
                        self.bot.db.set_onboarding(member.id, "completed", 0)
                        await self.apply_onboarding_access(member)

            except discord.Forbidden:
                log.warning("Could not update platform role for %s.", member.id)
            except discord.HTTPException:
                log.exception("Could not update platform role for %s.", member.id)

            return True

        if payload.channel_id == ROLE_SELECTION_CHANNEL and payload.message_id in {
            NOTIFICATION_MESSAGE,
            self.notification_message_id(),
        }:
            configured = NOTIFICATION_ROLES.get(emoji_key)
            if not configured:
                return True

            role_id, label = configured

            member = await self.payload_member(payload)
            guild = self.bot.get_guild(GUILD_ID)

            if member is None or guild is None or member.bot:
                return True

            role = resolve_configured_role(guild, role_id, label)
            if role is None:
                log.warning("Notification role could not be resolved: %s.", label)
                return True

            try:
                if added and role not in member.roles:
                    await member.add_roles(
                        role,
                        reason="Notification role selected",
                    )
                elif not added and role in member.roles:
                    await member.remove_roles(
                        role,
                        reason="Notification role removed",
                    )
            except discord.Forbidden:
                log.warning("Could not update notification role for %s.", member.id)
            except discord.HTTPException:
                log.exception("Could not update notification role for %s.", member.id)

            return True

        return False

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID or member.bot:
            return

        self.bot.db.ensure_user(member.id)
        self.bot.db.set_onboarding(member.id, "exempt", 0)
        self.bot.db.set_onboarding(member.id, "ever_verified", 0)

        await self.apply_onboarding_access(member)
        await self.update_onboarding_dm(member)
        await self.send_welcome(member)
        await self.update_member_count()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return

        self.bot.db.delete_onboarding(member.id)
        await self.update_member_count()

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> None:
        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        async with self.reaction_member_lock(payload.user_id):
            if await self.handle_verification_reaction(payload, True):
                return
            await self.handle_reaction_roles(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> None:
        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        key = reaction_removal_key(
            payload.user_id,
            payload.channel_id,
            payload.message_id,
            payload.emoji,
        )

        if key in self.bot_managed_reaction_removals:
            self.bot_managed_reaction_removals.discard(key)
            return

        if locked_reaction_message(payload):
            return

        async with self.reaction_member_lock(payload.user_id):
            await self.handle_reaction_roles(payload, False)

    @app_commands.command(
        name="setup_verification_reactions",
        description="Add checkmarks to the existing onboarding messages.",
    )
    @staff_only()
    async def setup_verification_reactions(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        targets = {
            (RULES_CHANNEL, RULES_MESSAGE),
            (BOOSTER_RULES_CHANNEL, BOOSTER_RULES_MESSAGE),
            (BULLETIN_CHANNEL, BULLETIN_MESSAGE),
        }

        failed: list[str] = []

        for channel_id, message_id in targets:
            channel = await get_text_channel(self.bot, channel_id)

            if channel is None:
                failed.append(str(message_id))
                continue

            try:
                message = await channel.fetch_message(message_id)
                await message.add_reaction(CHECKMARK)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                failed.append(str(message_id))

        if failed:
            await interaction.followup.send(
                "Failed message IDs: " + ", ".join(failed),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "Verification reactions added.",
                ephemeral=True,
            )

    @app_commands.command(
        name="setup_league_roles",
        description="Create the league reaction-role panel in this channel.",
    )
    @staff_only()
    async def setup_league_roles(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        lines = ["Choose exactly one league:"]

        for emoji_text, role_id in LEAGUE_ROLES.items():
            role = resolve_configured_role(
                interaction.guild,
                role_id,
                LEAGUE_ROLE_NAMES.get(emoji_text, ""),
            )
            if role is not None:
                lines.append(f"{parse_emoji(emoji_text)} {role.mention}")

        message = await interaction.channel.send("\n".join(lines))

        for emoji_text in LEAGUE_ROLES:
            await message.add_reaction(parse_emoji(emoji_text))

        self.bot.db.set_setting("league_message", str(message.id))

        await interaction.followup.send(
            f"League panel created. Message ID: {message.id}",
            ephemeral=True,
        )

    @app_commands.command(
        name="setup_notification_roles",
        description="Create the notification reaction-role panel in this channel.",
    )
    @staff_only()
    async def setup_notification_roles(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        lines = ["Choose any notification roles you want:"]

        for emoji_text, (role_id, label) in NOTIFICATION_ROLES.items():
            role = resolve_configured_role(interaction.guild, role_id, label)
            if role is not None:
                lines.append(f"{emoji_text} {label}: {role.mention}")

        message = await interaction.channel.send("\n".join(lines))

        for emoji_text in NOTIFICATION_ROLES:
            await message.add_reaction(emoji_text)

        self.bot.db.set_setting("notification_message", str(message.id))

        await interaction.followup.send(
            f"Notification panel created. Message ID: {message.id}",
            ephemeral=True,
        )

    @app_commands.command(
        name="refresh_onboarding",
        description="Show the current onboarding behavior.",
    )
    @staff_only()
    async def refresh_onboarding(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.send_message(
            "Existing members are exempt. Onboarding is applied automatically only when a new member joins.",
            ephemeral=True,
        )

    @app_commands.command(
        name="membercount",
        description="Show the current server member count.",
    )
    async def membercount(
        self,
        interaction: discord.Interaction,
    ) -> None:
        count = (
            interaction.guild.member_count
            or len(interaction.guild.members)
        )

        await interaction.response.send_message(
            f"Server members: {count}",
            ephemeral=True,
        )
