"""Discord.py Cogs for the War Robots Guide Mute bot."""

from mute_bot.cogs.giveaways import GiveawaysCog
from mute_bot.cogs.interactions import InteractionsCog
from mute_bot.cogs.moderation import ModerationCog
from mute_bot.cogs.onboarding import OnboardingCog

__all__ = [
    "GiveawaysCog",
    "InteractionsCog",
    "ModerationCog",
    "OnboardingCog",
]
