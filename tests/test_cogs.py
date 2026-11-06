from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import discord
import pytest
from mute_bot.bot import MuteBot
from mute_bot.cogs.interactions import InteractionsCog
from mute_bot.cogs.onboarding import OnboardingCog
from mute_bot.config import (
    GUILD_ID,
    LEAGUE_MESSAGE,
    NOTIFICATION_MESSAGE,
    ROLE_SELECTION_CHANNEL,
    RULES_CHANNEL,
    RULES_MESSAGE,
)
from mute_bot.database import Database


@pytest.mark.asyncio
async def test_interactions_on_message_deletes_banned_text_without_replying(tmp_path, monkeypatch) -> None:
    db = Database(tmp_path / "test.sqlite3")
    bot = MuteBot(db=db)
    cog = InteractionsCog(bot)

    deleted = AsyncMock(return_value=True)
    replied = AsyncMock()
    monkeypatch.setattr("mute_bot.cogs.interactions.delete_message", deleted)
    monkeypatch.setattr("mute_bot.cogs.interactions.reliable_message_reply", replied)

    member = MagicMock(spec=discord.Member)
    member.id = 123
    member.bot = False
    member.roles = []
    guild = SimpleNamespace(id=GUILD_ID)
    msg = SimpleNamespace(
        id=999,
        guild=guild,
        author=member,
        webhook_id=None,
        content="@Mute enlighten me hitler",
        attachments=[],
        raw_mentions=[],
    )

    await cog.on_message(msg)
    deleted.assert_awaited_once_with(msg)
    replied.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_resolves_saved_panel_ids_and_ignores_bot_managed_removals(tmp_path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    bot = MuteBot(db=db)
    cog = OnboardingCog(bot)

    assert cog.league_message_id() == LEAGUE_MESSAGE
    assert cog.notification_message_id() == NOTIFICATION_MESSAGE

    db.set_setting("league_message", "999888777")
    assert cog.league_message_id() == 999888777

    # Bot-managed reaction removal is ignored once and cleared
    key = (42, ROLE_SELECTION_CHANNEL, 999888777, "league_gold:1524797623385591859")
    cog.bot_managed_reaction_removals.add(key)

    payload = SimpleNamespace(
        user_id=42,
        guild_id=GUILD_ID,
        channel_id=ROLE_SELECTION_CHANNEL,
        message_id=999888777,
        emoji=discord.PartialEmoji(name="league_gold", id=1524797623385591859),
    )
    cog.handle_reaction_roles = AsyncMock()
    await cog.on_raw_reaction_remove(payload)
    cog.handle_reaction_roles.assert_not_awaited()
    assert key not in cog.bot_managed_reaction_removals


@pytest.mark.asyncio
async def test_locked_verification_reaction_remove_does_not_revoke_onboarding(tmp_path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    db.set_onboarding(77, "rules", 1)
    bot = MuteBot(db=db)
    cog = OnboardingCog(bot)

    payload = SimpleNamespace(
        user_id=77,
        guild_id=GUILD_ID,
        channel_id=RULES_CHANNEL,
        message_id=RULES_MESSAGE,
        emoji=discord.PartialEmoji(name="✅"),
    )
    await cog.on_raw_reaction_remove(payload)
    assert db.onboarding(77)["rules"] == 1


@pytest.mark.asyncio
async def test_all_expected_slash_commands_registered(tmp_path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    bot = MuteBot(db=db)
    await bot.register_cogs()
    command_names = {cmd.name for cmd in bot.tree.get_commands()}
    expected = {
        "ban",
        "mute",
        "unmute",
        "warn",
        "warnings",
        "clearwarnings",
        "setup_verification_reactions",
        "setup_league_roles",
        "setup_notification_roles",
        "refresh_onboarding",
        "giveaway",
        "endgiveaway",
        "rerollgiveaway",
        "membercount",
    }
    assert expected.issubset(command_names)
