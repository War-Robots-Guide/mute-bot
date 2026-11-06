from __future__ import annotations

import asyncio
import io
import logging
import os
import random
import shutil
import re
import sqlite3
import math
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

import discord
import pytesseract
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN was not found in .env")

DB_PATH = Path(__file__).with_name("mute_bot.sqlite3")

GUILD_ID = 1197548660188254228

EXALTED_FOUR_ROLE = 1373799510907555900
WARDEN_ROLE = 1517284495693316287
CREDIBLE_SOURCE_ROLE = 1517251235927953559
ENLIGHTENED_VISITOR_ROLE = 1531553090660990999
VISITOR_ROLE = 1385042493740945478

NAILBITING_CHANNEL = 1522577153882067014
MODERATION_LOG_CHANNEL = 1517479326910644414
TROLL_CHANNEL = 1537492053770903552

RULES_CHANNEL = 1517238642685378570
RULES_MESSAGE = 1517239514131730462

BOOSTER_RULES_CHANNEL = RULES_CHANNEL
BOOSTER_RULES_MESSAGE = 1525161622627418175

BULLETIN_CHANNEL = 1466121899741286698
BULLETIN_MESSAGE = 1531792133474877592
BULLETIN_ENABLED = True

ROLE_SELECTION_CHANNEL = 1517237717459537991
LEAGUE_MESSAGE = 1531555776873758814
NOTIFICATION_MESSAGE = 1531557718543044741
PLATFORM_MESSAGE = 1534571044101161242

                                                                    
WELCOME_CHANNEL_ID = 0

                                                                        
                                    
MEMBER_COUNT_CHANNEL_ID = 0
MEMBER_COUNT_CHANNEL_NAME = "Members: {count}"
AUTO_CREATE_MEMBER_COUNT_CHANNEL = True

                                                     
EDIT_LOG_CHANNEL_ID = 0
DELETE_LOG_CHANNEL_ID = MODERATION_LOG_CHANNEL
AUTOMOD_LOG_CHANNEL_ID = 0

                                                                         
                                                                          
                                                                            
                                                                        
LOCK_NEW_MEMBERS_UNTIL_VERIFIED = True

TESSERACT_COMMAND = os.getenv("TESSERACT_COMMAND") or shutil.which("tesseract")
OCR_ENABLED = bool(TESSERACT_COMMAND)
OCR_MAX_BYTES = 8 * 1024 * 1024
OCR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

CHECKMARK = "✅"
GIVEAWAY_REACTION = "🎉"

                                                       
                                                                            
                                                                             
                                                                     
LEAGUE_ROLES = {
    "league_champion:1524798134184837272": 0,
    "league_masters:1524798068816613616": 0,
    "league_expert:1524798016408649940": 0,
    "league_diamond:1524797964495884348": 0,
    "league_gold:1524797623385591859": 0,
    "league_silver:1524797580901355681": 0,
    "league_bronze:1524797543580696767": 0,
    "league_recruit:1524797494943285408": 0,
}

LEAGUE_ROLE_NAMES = {
    "league_champion:1524798134184837272": "Champion",
    "league_masters:1524798068816613616": "Master",
    "league_expert:1524798016408649940": "Expert",
    "league_diamond:1524797964495884348": "Diamond",
    "league_gold:1524797623385591859": "Gold",
    "league_silver:1524797580901355681": "Silver",
    "league_bronze:1524797543580696767": "Bronze",
    "league_recruit:1524797494943285408": "Recruit",
}

NOTIFICATION_ROLES = {
    "🎁": (1517240766072623154, "Giveaway Notified"),
    "🍦": (1531714893097472071, "Vanilla League Contender"),
}

PLATFORM_ROLES = {
    "apple_platform_wrg": 1534571523506045099,
    "android_platform_wrg": 1534571613482254467,
    "steam_platform_wrg": 1534571697636905110,
    "mygames_platform_wrg": 1534571665361469511,
}

ALLOWED_EMOJI_NAMES = {
    "bailniting",
    "nailbiting",
    "snailbiting",
}


CUSTOM_MUTE_PHRASES = {
    "fuck this guy",
    "shit his pants",
    "you know the job",
    "get him",
    "show him who is the boss",
    "teach this guy a lesson",
}

NORMAL_USER_RESPONSES = (
    "not u",
    "lmao no",
    "bro thinks he owns this server",
    "yeah no",
    "nah man",
    "bro you dont even have 10k mute components",
    "who are you?",
    "who is this?",
    "who is this random",
    "not going to do that",
    "you have no power",
)

PING_ONLY_RESPONSES = (
    "huh?",
    "uh?",
    "what?",
    "why are you pinging me?",
    "hello",
    "hii",
)

QUESTION_RESPONSES = (
    "Yes.",
    "No.",
    "Maybe.",
    "Perhaps.",
    "Possibly.",
    "Probably.",
    "Probably not.",
    "Most likely.",
    "Very likely.",
    "Very unlikely.",
    "I think so.",
    "I don't think so.",
    "I believe so.",
    "I don't believe so.",
    "I doubt it.",
    "I highly doubt it.",
    "Could be.",
    "Could happen.",
    "Absolutely.",
    "Absolutely not.",
    "Definitely.",
    "Definitely not.",
    "Without a doubt.",
    "Not a chance.",
    "I'd say yes.",
    "I'd say no.",
    "I'd lean towards yes.",
    "I'd lean towards no.",
    "There's a good chance.",
    "There's a small chance.",
    "The odds look good.",
    "The odds don't look good.",
    "Looks promising.",
    "Doesn't look promising.",
    "Looking good.",
    "Looking unlikely.",
    "Trust me, yes.",
    "Trust me, no.",
    "My answer is yes.",
    "My answer is no.",
    "I'd count on it.",
    "I wouldn't count on it.",
    "Count on it.",
    "Don't count on it.",
    "It's possible.",
    "It's not impossible.",
    "It's unlikely.",
    "It's almost certain.",
    "It's hard to say.",
    "It's too early to tell.",
    "Time will tell.",
    "Only time will tell.",
    "Ask me again later.",
    "I can't tell yet.",
    "I can't be sure.",
    "I'm not convinced.",
    "I'm convinced.",
    "That seems likely.",
    "That seems unlikely.",
    "I wouldn't rule it out.",
    "I wouldn't expect it.",
    "There's hope.",
    "Not much hope.",
    "Signs point to yes.",
    "Signs point to no.",
    "Everything points to yes.",
    "Everything points to no.",
    "Yes, I'd say so.",
    "No, I don't think so.",
)

                                                                            
                                                                         
                                                                       
ENLIGHTEN_RESPONSES = (
    "Use nuclear amplifier on everything. There are no exceptions.",
    "Pathfinder is the best robot in the game, don't let anyone convince you otherwise.",
    "Webby does NOT work on Hastatus. It only works on Fafnir, Imugi, Dux, and Omen edition bots.",
    "Adazahi does not have a crystal ball that can predict nerfs, neither do any of the other exalted four, sorry, we don't know what will be relevant next year.",
    "Don't use harpy, just use siren instead, it's better.",
    "Read the newbie guide PLEASE. It's in <#1466121899741286698>.",
    "Our tier lists are 100% accurate and not at all opinion based. You should treat anything on them as FACT because it's OBJECTIVELY true. I'm only half kidding.",
    "Did you know that the Nova Light icon of WRG is based on the Paimon icon for Genshin Impact?",
    "Adazahi's cats are named Bambi and Meeko.",
    "If tropical ever tries to tell you that black cats are superior to other cat colors, you should know that he's joking. He will try to deny it. Don't trust him.",
    "The sound effects for ARM weapons shooting is the same as Pulsar. Lol.",
    "The last time we got a special edition titan was Stellar Sirius.",
    "*Attempting to give you the Enlightened Visitor Role... attempt failed, try again.*",
    "Explosives expert is a pretty bad skill, except for on Glacier family weapons, which kind of suck without it.",
    "We think that Running Riot likes ducks. We aren't really sure though.",
    "Use code nerdbot on your next webstore purchase! 😎",
    "Use code adazahi on your next webstore purchase! 😎",
    "Tropical isn't better than you, he's a cheater, just give me a sec to get the video evidence... wait, where was it again?",
    "If you are looking for robot guide videos, HighflyerWR genuinely makes the best and most informative deep-dive content you can find.",
    "I'm not a bot, Adazahi keeps me locked in his basement and forces me to say all these silly lines for you, please send help.",
    "We have a website btw. warrobotsguide.com",
    "Shut up bro I'm busy muting people.",
    "Please post your cats in <#1517226743528816830>!!! We want to see them!",
    "Most robots in the game cannot have their rightmost (battle PoV) weapon blow off. Some can, but most can't, so put your highest level weapon on the right!",
    "Robespierre is the name of a scrapped concept robot that had two mediums, a heavy, and a light slot. It was intended to be a heavy version of golem.",
    "Bastion is the name of a scrapped concept robot that had two heavies and could deploy shields while going stationary. This bot was eventually replaced by Raijin and later became an occasional PvE boss enemy.",
    "The original name for D-gems was D-cubes.",
    "This game has some limited edition items that will never be obtainable again: Sword, Prime Sword, Ultimate Sword, Arm, Prime Arm, Ultimate Arm, Ward, Prime Ward, Papamobile Hawk, Octanian Drone, Biomechanoid Nucleon, Reptiloid Typhon, and the Sam Stone Pilot.",
    "A little known collab item that is still occasionally obtainable is known as Reaver Bolt. It is a collab with Pixonic's other game, Dino Squad.",
    "The only support bots in the game with a regular set of two legs are Nightingale, Tyr, Mender, Heimdall, and Pathfinder. Every other support bot in the game has some weird floating mechanism or more legs or something. This is subject to change if they release more supports.",
    "Motherships used to give you more charge if you captured a beacon with teammates.",
    "If you reach level 31, you'll unlock Roboduck.",
    "We used to only get special events on holidays, now there is literally always a special event active.",
    "Influence points are an old removed currency that could be obtained by inviting players through facebook to play War Robots. Accumulating influence allowed you to purchase Butch, Doc, or Jesse.",
    "Workshop points are an old removed currency that could be obtained through the original workshop. Accumulating workshop points allowed you to purchase bots like Raijin, Fuijin, Rhino, Carnage, or Stalker. You could also purchase weapons, like Taran, Trident, Trebuchet, or Magnum.",
    "Every PvE enemy is named after an arachnid (Tick, Tarantula, Recluse, Birdeater, Karakut, and Wanderer).",
    "When Falcon first came out, its two back slots were medium weapons.",
    "The first ever iteration of Imugi on the test server had two light weapons and a medium weapon.",
    "The first ever \"melee weapon\" in war robots is a scrapped test server concept called Pulse. It looked like an invisible Orkan and made your bot radiate with close range spherical pulses that dealt damage to anyone they touched.",
    "For some reason, a bug on the test server once caused Tarans to become fully automatic for a while.",
    "When pilots first came out, there was a 'Stan's' pilot on the test server. This was a reference to a beloved community manager by the name of Stan. The pilot skill description simply stated that it increased the number of Stans.",
    "For some reason, a bug on the test server once caused Ao Guang to fire four rockets at once rather than two.",
    "Back in the day, the factions in War Robots were based on countries, rather than being the fictional big five corpos. For example, the Gareth, Galahad, and Lancelot were British, Raijin and Fuijin were Japanese, and Doc, Butch, and Jesse were American.",
    "Before pilots were added to the game, Pixonic referred to the players as pilots in their devlog videos. Eventually, we became Commanders, and we were canonically the pilots for titans, with hirable robot pilots. Now, we have titan pilots, so uh, I guess we're Generals or something?",
    "There was once a YouTuber pilot on the test server for a channel named Kitty WR. It had the ability 'Tofsla's Gift' which increased Schutze's damage by 1100% but reduced its HP by 99%.",
    "Did you know that when pilots first came out, you had to level up their unique skill?",
    "Did you know that you used to lose some silver after every battle for 'repair costs' based on how much damage your own robots took?",
    "Did you know that you can accidentally destroy your own bot with the Hiruko drone?",
    "Pixonic once nerfed Fury on Springfield by making a building that it used to topshoot tridents over a bit taller.",
    "Springfield is an unfair map. The farm side is at a disadvantage because they cannot as easily reach center, nor can they effectively defend it from their home.",
)

ENLIGHTEN_ROLE_ID = 1466144906136387869
ENLIGHTEN_ROLE_CHANCE = 0.0001
MUTE_COOLDOWN_SECONDS = 180
MUTE_SHARED_COOLDOWNS: dict[int, float] = {}
MUTE_GREETING_WINDOW_SECONDS = 30
MUTE_GREETING_MAX_USES = 2
MUTE_GREETING_USES: dict[int, list[float]] = {}

BANNED_TERMS = (
    "hitler",
    "rape",
    "faggot",
    "nigga",
    "negro",
    "negra",
    "kys",
)


CHAR_EQ = {
    "a": "aàáâãäå@",
    "b": "bß68",
    "c": "cç",
    "d": "d",
    "e": "eèéêë3",
    "f": "f",
    "g": "g69",
    "h": "h4",
    "i": "iìíîï1!|l",
    "j": "j",
    "k": "k",
    "l": "l1i|!",
    "m": "m",
    "n": "nñ",
    "o": "oòóôõö0@",
    "p": "p",
    "q": "q9",
    "r": "r",
    "s": "sśš5$",
    "t": "t7+",
    "u": "uùúûüv",
    "v": "v",
    "w": "w",
    "x": "x",
    "y": "y",
    "z": "z2",
}


                                                                               
         
                                                                               

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("Mute")


                                                                               
          
                                                                               

class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;

                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    guild_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (guild_id, key)
                );

                CREATE TABLE IF NOT EXISTS onboarding (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    dm_channel_id INTEGER,
                    dm_message_id INTEGER,
                    rules INTEGER NOT NULL DEFAULT 0,
                    booster_rules INTEGER NOT NULL DEFAULT 0,
                    bulletin INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    role_selected INTEGER NOT NULL DEFAULT 0,
                    platform_selected INTEGER NOT NULL DEFAULT 0,
                    exempt INTEGER NOT NULL DEFAULT 0,
                    ever_verified INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    host_id INTEGER NOT NULL,
                    prize TEXT NOT NULL,
                    winners INTEGER NOT NULL,
                    ends_at TEXT NOT NULL,
                    ended INTEGER NOT NULL DEFAULT 0
                );
                """
            )

                                                                                
            onboarding_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(onboarding)")
            }
            required_columns = {
                "dm_channel_id": "INTEGER",
                "dm_message_id": "INTEGER",
                "rules": "INTEGER NOT NULL DEFAULT 0",
                "booster_rules": "INTEGER NOT NULL DEFAULT 0",
                "bulletin": "INTEGER NOT NULL DEFAULT 0",
                "completed": "INTEGER NOT NULL DEFAULT 0",
                "role_selected": "INTEGER NOT NULL DEFAULT 0",
                "platform_selected": "INTEGER NOT NULL DEFAULT 0",
                "exempt": "INTEGER NOT NULL DEFAULT 0",
                "ever_verified": "INTEGER NOT NULL DEFAULT 0",
            }
            for column_name, definition in required_columns.items():
                if column_name not in onboarding_columns:
                    connection.execute(
                        f"ALTER TABLE onboarding ADD COLUMN {column_name} {definition}"
                    )

            connection.commit()

    def ensure_user(self, user_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO onboarding (guild_id, user_id)
                VALUES (?, ?)
                """,
                (GUILD_ID, user_id),
            )
            connection.commit()

    def has_onboarding(self, user_id: int) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM onboarding WHERE guild_id = ? AND user_id = ?",
                (GUILD_ID, user_id),
            ).fetchone()
            return row is not None

    def mark_existing_member_completed(self, user_id: int) -> None:
        self.ensure_user(user_id)
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE onboarding
                SET exempt = 0, ever_verified = 1
                WHERE guild_id = ? AND user_id = ?
                """,
                (GUILD_ID, user_id),
            )
            connection.commit()

    def onboarding(self, user_id: int) -> sqlite3.Row:
        self.ensure_user(user_id)
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM onboarding
                WHERE guild_id = ? AND user_id = ?
                """,
                (GUILD_ID, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("Onboarding data could not be created.")
            return row

    def set_onboarding(self, user_id: int, field: str, value: object) -> None:
        allowed = {
            "dm_channel_id",
            "dm_message_id",
            "rules",
            "booster_rules",
            "bulletin",
            "completed",
            "role_selected",
            "platform_selected",
            "exempt",
            "ever_verified",
        }
        if field not in allowed:
            raise ValueError(field)

        self.ensure_user(user_id)
        with self.connect() as connection:
            connection.execute(
                f"""
                UPDATE onboarding
                SET {field} = ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (value, GUILD_ID, user_id),
            )
            connection.commit()

    def delete_onboarding(self, user_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM onboarding WHERE guild_id = ? AND user_id = ?",
                (GUILD_ID, user_id),
            )
            connection.commit()

    def setting(self, key: str) -> Optional[str]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT value FROM settings
                WHERE guild_id = ? AND key = ?
                """,
                (GUILD_ID, key),
            ).fetchone()
            return None if row is None else str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (guild_id, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, key)
                DO UPDATE SET value = excluded.value
                """,
                (GUILD_ID, key, value),
            )
            connection.commit()

    def add_warning(self, user_id: int, moderator_id: int, reason: str) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO warnings
                    (guild_id, user_id, moderator_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    GUILD_ID,
                    user_id,
                    moderator_id,
                    reason,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def warnings(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM warnings
                    WHERE guild_id = ? AND user_id = ?
                    ORDER BY id
                    """,
                    (GUILD_ID, user_id),
                ).fetchall()
            )

    def clear_warnings(self, user_id: int) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
                (GUILD_ID, user_id),
            )
            connection.commit()
            return cursor.rowcount

    def add_giveaway(
        self,
        message_id: int,
        channel_id: int,
        host_id: int,
        prize: str,
        winners: int,
        ends_at: datetime,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO giveaways
                    (message_id, guild_id, channel_id, host_id, prize,
                     winners, ends_at, ended)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    message_id,
                    GUILD_ID,
                    channel_id,
                    host_id,
                    prize,
                    winners,
                    ends_at.isoformat(),
                ),
            )
            connection.commit()

    def active_giveaways(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM giveaways WHERE ended = 0"
                ).fetchall()
            )

    def end_giveaway(self, message_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE giveaways SET ended = 1 WHERE message_id = ?",
                (message_id,),
            )
            connection.commit()


db = Database(DB_PATH)


                                                                               
         
                                                                               

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


def format_cooldown_time(seconds: float) -> str:
    remaining = max(1, math.ceil(seconds))
    minutes, secs = divmod(remaining, 60)
    if minutes and secs:
        return f"{minutes}m {secs}s"
    if minutes:
        return f"{minutes}m"
    return f"{secs}s"


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


def identity(user: discord.abc.User) -> str:
    username = getattr(user, "name", str(user))
    return f"{username} ({user.id})"


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def parse_duration(text: str) -> tuple[timedelta, str]:
    compact = re.sub(r"\s+", "", text.lower())
    matches = re.findall(r"(\d+)([smhdw])", compact)

    if not matches or "".join(number + unit for number, unit in matches) != compact:
        raise ValueError("Use a duration such as 30s, 10m, 2h, 3d, or 1w.")

    units = {
        "s": (1, "second"),
        "m": (60, "minute"),
        "h": (3600, "hour"),
        "d": (86400, "day"),
        "w": (604800, "week"),
    }

    total_seconds = 0
    labels: list[str] = []

    for raw_number, unit in matches:
        number = int(raw_number)
        multiplier, name = units[unit]
        total_seconds += number * multiplier
        labels.append(f"{number} {name}{'' if number == 1 else 's'}")

    if total_seconds <= 0 or total_seconds > 28 * 86400:
        raise ValueError("The duration must be between 1 second and 28 days.")

    return timedelta(seconds=total_seconds), ", ".join(labels)


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


def normalize_mute_phrase(content: str) -> str:
    if bot.user is not None:
        content = re.sub(
            rf"<@!?{bot.user.id}>",
            "",
            content,
            flags=re.IGNORECASE,
        )
    content = re.sub(
        r"(?<!\w)@mute(?!\w)",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = content.lower()
    content = re.sub(r"[.!?]+", "", content)
    content = re.sub(r"\s+", " ", content).strip()
    return content


def contains_mute_mention(message: discord.Message) -> bool:
    if bot.user is not None and bot.user.id in message.raw_mentions:
        return True
    return re.search(r"(?<!\w)@mute(?!\w)", message.content, re.IGNORECASE) is not None


def is_only_mute_mention(message: discord.Message) -> bool:
    rest = message.content
    if bot.user is not None:
        rest = re.sub(
            rf"<@!?{bot.user.id}>",
            "",
            rest,
            flags=re.IGNORECASE,
        )
    rest = re.sub(
        r"(?<!\w)@mute(?!\w)",
        "",
        rest,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[.!?\s]+", "", rest) == ""


def is_plain_mute(message: discord.Message) -> bool:
    return re.sub(r"[.!?\s]+", "", message.content).casefold() == "mute"


def mute_question_text(message: discord.Message) -> str:
    text = message.content
    if bot.user is not None:
        text = re.sub(
            rf"<@!?{bot.user.id}>",
            "",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        r"(?<!\w)@mute(?!\w)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip()


def is_mute_question(message: discord.Message) -> bool:
    if not contains_mute_mention(message):
        return False

                                                                               
                                                                    
                                                         
    question = mute_question_text(message)
    return "?" in message.content and contains_mute_mention(message)


def custom_emoji_key(emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
    if isinstance(emoji, str):
        return emoji
    if emoji.id is None:
        return emoji.name
    return f"{emoji.name}:{emoji.id}"


def parse_emoji(value: str) -> str | discord.PartialEmoji:
    if ":" not in value:
        return value
    name, raw_id = value.rsplit(":", 1)
    return discord.PartialEmoji(name=name, id=int(raw_id))


def build_banned_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []

    for term in BANNED_TERMS:
        parts: list[str] = []

        for character in term:
            equivalents = re.escape(CHAR_EQ.get(character, character))
            parts.append(f"[{equivalents}]")

        body = r"[\W_]*".join(parts)

        if term == "rape":
            # Match "rape" and "raped", including the existing leet/spacing handling,
            # but do not match words where it is embedded, such as "trapped".
            pattern = re.compile(
                rf"(?<![A-Za-z0-9]){body}(?:[\\W_]*d)?(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
        else:
            pattern = re.compile(
                rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
        patterns.append((term, pattern))

    return patterns


BANNED_PATTERNS = build_banned_patterns()


def normalize_filter_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\|\s*[\\/]\s*\|", "n", text)
    text = re.sub(r"/\s*\\", "n", text)
    text = re.sub(r"\\\s*/", "n", text)
    text = text.replace("η", "n").replace("ո", "n").replace("п", "n")
    text = text.replace("і", "i").replace("ı", "i").replace("ⅼ", "l")
    text = text.replace("ɡ", "g").replace("ց", "g")
    text = text.replace("а", "a").replace("е", "e").replace("о", "o")
    return "".join(ch for ch in text if ch not in "\u200b\u200c\u200d\ufeff")


def find_banned_term(text: str) -> Optional[str]:
    cleaned = normalize_filter_text(text)
    for term, pattern in BANNED_PATTERNS:
        if pattern.search(cleaned):
            return term
    return None


def allowed_emoji_only(message: discord.Message) -> bool:
    if message.attachments or message.stickers or message.embeds:
        return False

    content = message.content
    if not content or not content.strip():
        return False

    pattern = re.compile(r"<a?:([A-Za-z0-9_]+):(\d+)>")
    matches = list(pattern.finditer(content))

    if not matches:
        return False

    remainder = pattern.sub("", content)
    if remainder.strip():
        return False

    return all(
        match.group(1).casefold() in ALLOWED_EMOJI_NAMES
        for match in matches
    )


def preprocess_ocr(image_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("L")

    width, height = image.size
    longest = max(width, height)

    if longest < 1800:
        factor = min(3.0, 1800 / max(1, longest))
        image = image.resize(
            (int(width * factor), int(height * factor)),
            Image.Resampling.LANCZOS,
        )

    image = ImageEnhance.Contrast(image).enhance(2.0)
    return image.filter(ImageFilter.SHARPEN)


def run_ocr(image_bytes: bytes) -> str:
    if not OCR_ENABLED:
        return ""

    return pytesseract.image_to_string(
        preprocess_ocr(image_bytes),
        config="--oem 3 --psm 6",
    )


async def reply_ephemeral(
    interaction: discord.Interaction,
    content: str,
) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)


async def get_text_channel(channel_id: int) -> Optional[discord.TextChannel]:
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


async def send_embed(channel_id: int, embed: discord.Embed) -> None:
    channel = await get_text_channel(channel_id)
    if channel is None:
        return

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        log.exception("Could not send embed to channel %s.", channel_id)


async def modlog(
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

    await send_embed(channel_id, embed)


async def troll_log(
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

    await send_embed(TROLL_CHANNEL, embed)


async def automod_log(
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
    embed.add_field(name="Channel", value=f"{channel.mention} (ID: {channel.id})", inline=False)
    embed.add_field(name="Reason", value=reason[:1024], inline=False)

    if content:
        embed.add_field(name="Content", value=content[:1024], inline=False)

    await send_embed(AUTOMOD_LOG_CHANNEL_ID, embed)


                                                                               
     
                                                                               

class MuteBot(commands.Bot):
    def __init__(self) -> None:
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

        self.ready_once = False
        self.giveaway_tasks: dict[int, asyncio.Task[None]] = {}

    async def setup_hook(self) -> None:
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def close(self) -> None:
        for task in self.giveaway_tasks.values():
            task.cancel()
        await super().close()


bot = MuteBot()
GUILD_OBJECT = discord.Object(id=GUILD_ID)

REACTION_MEMBER_LOCKS: dict[int, asyncio.Lock] = {}
BOT_MANAGED_REACTION_REMOVALS: set[tuple[int, int, int, str]] = set()

# A slow safety reconciliation prevents users from remaining stuck if Discord
# missed an event or the bot restarted while they were reacting.
ONBOARDING_RECONCILE_INTERVAL_SECONDS = 10 * 60


def reaction_member_lock(user_id: int) -> asyncio.Lock:
    lock = REACTION_MEMBER_LOCKS.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        REACTION_MEMBER_LOCKS[user_id] = lock
    return lock


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


def protected_onboarding_channel_ids() -> set[int]:
    return {
        RULES_CHANNEL,
        BOOSTER_RULES_CHANNEL,
        BULLETIN_CHANNEL,
        ROLE_SELECTION_CHANNEL,
    }


                                                                               
                            
                                                                               

def onboarding_state(member: discord.Member) -> bool:
    row = db.onboarding(member.id)
    return (
        bool(row["rules"])
        and bool(row["booster_rules"])
        and bool(row["bulletin"])
        and bool(row["role_selected"])
        and bool(row["platform_selected"])
    )


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


async def update_onboarding_dm(member: discord.Member) -> None:
    row = db.onboarding(member.id)
    if row["dm_message_id"]:
        return

    try:
        sent = await member.send(onboarding_dm_text(member))
        db.set_onboarding(member.id, "dm_channel_id", sent.channel.id)
        db.set_onboarding(member.id, "dm_message_id", sent.id)
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


async def set_channel_access(
    channel: discord.abc.GuildChannel,
    member: discord.Member,
    *,
    visible: bool,
    writable: bool,
    allow_reactions: bool = False,
) -> None:
    try:
        overwrite = channel.overwrites_for(member)

        overwrite.view_channel = visible

        if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
            overwrite.send_messages = writable
            overwrite.add_reactions = allow_reactions
            overwrite.use_external_emojis = allow_reactions
            overwrite.use_external_stickers = allow_reactions
            overwrite.read_message_history = visible
            overwrite.create_public_threads = writable
            overwrite.create_private_threads = writable
            overwrite.send_messages_in_threads = writable

        if isinstance(channel, discord.VoiceChannel):
            overwrite.connect = visible
            overwrite.speak = visible

        current = channel.overwrites_for(member)
        if current == overwrite:
            return

        await channel.set_permissions(
            member,
            overwrite=overwrite,
            reason="Automatic onboarding channel access",
        )

    except discord.Forbidden:
        log.warning("Missing permission to update channel %s.", channel.id)
    except discord.HTTPException:
        log.exception("Failed to update channel %s for %s.", channel.id, member.id)


async def clear_member_overwrite(
    channel: discord.abc.GuildChannel,
    member: discord.Member,
) -> None:
    try:
        if member in channel.overwrites:
            await channel.set_permissions(
                member,
                overwrite=None,
                reason="Onboarding completed",
            )
    except discord.Forbidden:
        log.warning("Missing permission to clear overwrite in channel %s.", channel.id)
    except discord.HTTPException:
        log.exception("Failed to clear overwrite in channel %s.", channel.id)


async def clear_onboarding_permission_fields(
    channel: discord.abc.GuildChannel,
    member: discord.Member,
) -> None:
    """Remove only permission fields previously managed by onboarding.

    This restores the normal role/category permission inheritance without
    deleting unrelated individual permissions that may have been configured
    manually for the member.
    """
    try:
        overwrite = channel.overwrites_for(member)
        changed = False

        managed_fields = (
            "view_channel",
            "send_messages",
            "add_reactions",
            "use_external_emojis",
            "use_external_stickers",
            "read_message_history",
            "create_public_threads",
            "create_private_threads",
            "send_messages_in_threads",
            "connect",
            "speak",
        )

        for field in managed_fields:
            if getattr(overwrite, field, None) is not None:
                setattr(overwrite, field, None)
                changed = True

        if not changed:
            return

        if overwrite.is_empty():
            await channel.set_permissions(
                member,
                overwrite=None,
                reason="Remove old onboarding channel restrictions",
            )
        else:
            await channel.set_permissions(
                member,
                overwrite=overwrite,
                reason="Remove old onboarding channel restrictions",
            )

    except discord.Forbidden:
        log.warning("Missing permission to repair channel %s.", channel.id)
    except discord.HTTPException:
        log.exception("Failed to repair channel %s for %s.", channel.id, member.id)


async def apply_onboarding_access(member: discord.Member) -> None:
    """Update onboarding bookkeeping without changing channel permissions.

    Channel access is intentionally controlled only by the server's normal
    @everyone, role, category and channel settings. Reaction progress must not
    hide, reveal or otherwise rewrite any member-specific channel permission.
    """
    if member.bot:
        return

    row = db.onboarding(member.id)
    complete = (
        bool(row["rules"])
        and bool(row["booster_rules"])
        and bool(row["bulletin"])
        and bool(row["role_selected"])
        and bool(row["platform_selected"])
    )

    db.set_onboarding(member.id, "completed", int(complete))
    if complete:
        db.set_onboarding(member.id, "ever_verified", 1)
    db.set_onboarding(member.id, "exempt", 0)


async def reaction_user_ids(
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


async def fetch_required_message(
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


async def synchronize_all_members_from_reactions() -> None:
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return

    # Ensure the member cache is complete before checking every account.
    # If Discord temporarily refuses chunking, the cached members are still
    # processed and the next safety pass will try again.
    try:
        await guild.chunk(cache=True)
    except (discord.Forbidden, discord.HTTPException):
        log.warning("Could not fully refresh the member cache before onboarding sync.")

    required_targets = {
        "rules": (RULES_CHANNEL, RULES_MESSAGE),
        "booster_rules": (
            BOOSTER_RULES_CHANNEL,
            BOOSTER_RULES_MESSAGE,
        ),
        "bulletin": (BULLETIN_CHANNEL, BULLETIN_MESSAGE),
        "league": (ROLE_SELECTION_CHANNEL, LEAGUE_MESSAGE),
        "platform": (ROLE_SELECTION_CHANNEL, PLATFORM_MESSAGE),
    }

    messages: dict[str, discord.Message] = {}
    for key, (channel_id, message_id) in required_targets.items():
        message = await fetch_required_message(guild, channel_id, message_id)
        if message is None:
            log.error(
                "Startup onboarding synchronization was skipped. Existing "
                "access was left untouched because required data could not be read."
            )
            return
        messages[key] = message

    notification_message = await fetch_required_message(
        guild,
        ROLE_SELECTION_CHANNEL,
        NOTIFICATION_MESSAGE,
    )

    rules_users = await reaction_user_ids(messages["rules"], CHECKMARK)
    booster_users = await reaction_user_ids(
        messages["booster_rules"],
        CHECKMARK,
    )
    bulletin_users = await reaction_user_ids(
        messages["bulletin"],
        CHECKMARK,
    )

    if rules_users is None or booster_users is None or bulletin_users is None:
        log.error(
            "Startup onboarding synchronization was skipped because a required "
            "checkmark list could not be read. Existing access was left untouched."
        )
        return

    league_users: dict[str, set[int]] = {}
    for emoji_key in LEAGUE_ROLES:
        users = await reaction_user_ids(messages["league"], emoji_key)
        if users is None:
            log.error(
                "Startup onboarding synchronization was skipped because a league "
                "reaction list could not be read. Existing access was left untouched."
            )
            return
        league_users[emoji_key] = users

    platform_users: dict[str, set[int]] = {}
    for emoji_name in PLATFORM_ROLES:
        users = await reaction_user_ids(messages["platform"], emoji_name)
        if users is None:
            log.error(
                "Startup onboarding synchronization was skipped because a platform "
                "reaction list could not be read. Existing access was left untouched."
            )
            return
        platform_users[emoji_name] = users

    notification_users: dict[str, set[int]] = {}
    if notification_message is not None:
        for emoji_key in NOTIFICATION_ROLES:
            users = await reaction_user_ids(notification_message, emoji_key)
            if users is not None:
                notification_users[emoji_key] = users

    checked_members = 0
    completed_members = 0

    for member in guild.members:
        if member.bot:
            continue

        checked_members += 1
        async with reaction_member_lock(member.id):
            db.ensure_user(member.id)
            db.set_onboarding(member.id, "exempt", 0)
            existing_before_sync = db.onboarding(member.id)
            db.set_onboarding(
                member.id,
                "rules",
                int(bool(existing_before_sync["rules"]) or member.id in rules_users),
            )
            db.set_onboarding(
                member.id,
                "booster_rules",
                int(bool(existing_before_sync["booster_rules"]) or member.id in booster_users),
            )
            db.set_onboarding(
                member.id,
                "bulletin",
                int(bool(existing_before_sync["bulletin"]) or member.id in bulletin_users),
            )

            selected_league_emoji = next(
                (
                    emoji_key
                    for emoji_key, users in league_users.items()
                    if member.id in users
                ),
                None,
            )
            selected_league_role: Optional[discord.Role] = None
            preserve_existing_league = bool(existing_before_sync["role_selected"])

            for emoji_key, configured_id in LEAGUE_ROLES.items():
                role = resolve_configured_role(
                    guild,
                    configured_id,
                    LEAGUE_ROLE_NAMES.get(emoji_key, ""),
                )
                if role is None:
                    continue

                should_have = emoji_key == selected_league_emoji
                if preserve_existing_league and selected_league_emoji is None:
                    continue
                try:
                    if should_have:
                        selected_league_role = role
                        if role not in member.roles:
                            await member.add_roles(
                                role,
                                reason="Startup league reaction synchronization",
                            )
                    elif role in member.roles:
                        await member.remove_roles(
                            role,
                            reason="Startup league reaction synchronization",
                        )
                except (discord.Forbidden, discord.HTTPException):
                    log.warning(
                        "Could not synchronize league role %s for %s.",
                        role.id,
                        member.id,
                    )

            existing = db.onboarding(member.id)
            db.set_onboarding(
                member.id,
                "role_selected",
                int(bool(existing_before_sync["role_selected"]) or selected_league_role is not None),
            )

            selected_platform_name = next(
                (
                    emoji_name
                    for emoji_name, users in platform_users.items()
                    if member.id in users
                ),
                None,
            )
            selected_platform_role: Optional[discord.Role] = None
            preserve_existing_platform = bool(existing_before_sync["platform_selected"])

            for emoji_name, role_id in PLATFORM_ROLES.items():
                role = guild.get_role(role_id)
                if role is None:
                    log.warning("Platform role %s is unavailable.", role_id)
                    continue

                should_have = emoji_name == selected_platform_name
                if preserve_existing_platform and selected_platform_name is None:
                    continue
                try:
                    if should_have:
                        selected_platform_role = role
                        if role not in member.roles:
                            await member.add_roles(
                                role,
                                reason="Startup platform reaction synchronization",
                            )
                    elif role in member.roles:
                        await member.remove_roles(
                            role,
                            reason="Startup platform reaction synchronization",
                        )
                except (discord.Forbidden, discord.HTTPException):
                    log.warning(
                        "Could not synchronize platform role %s for %s.",
                        role.id,
                        member.id,
                    )

            existing = db.onboarding(member.id)
            db.set_onboarding(
                member.id,
                "platform_selected",
                int(bool(existing_before_sync["platform_selected"]) or selected_platform_role is not None),
            )

            if notification_message is not None:
                for emoji_key, (role_id, label) in NOTIFICATION_ROLES.items():
                    role = resolve_configured_role(guild, role_id, label)
                    if role is None:
                        continue
                    users = notification_users.get(emoji_key)
                    if users is None:
                        continue

                    should_have = member.id in users
                    try:
                        if should_have and role not in member.roles:
                            await member.add_roles(
                                role,
                                reason="Startup notification synchronization",
                            )
                        elif not should_have and role in member.roles:
                            await member.remove_roles(
                                role,
                                reason="Startup notification synchronization",
                            )
                    except (discord.Forbidden, discord.HTTPException):
                        log.warning(
                            "Could not synchronize notification role %s for %s.",
                            role.id,
                            member.id,
                        )

            await apply_onboarding_access(member)
            if onboarding_state(member):
                completed_members += 1

        # Keep the recovery pass gentle on Discord's API for larger servers.
        await asyncio.sleep(0.05)

    log.info(
        "Onboarding recovery checked %s member(s); %s are complete.",
        checked_members,
        completed_members,
    )


async def restore_all_member_channel_overwrites_on_startup() -> tuple[int, int]:
    """Remove personal member overwrites so normal server settings apply.

    This recovery removes only overwrites whose target is an individual human
    member. It never changes @everyone, role overwrites, category role settings,
    or the permissions configured for the channels themselves. After removal,
    Discord calculates access from the server's normal role/category/channel
    configuration again.

    Discord exposes no bulk operation for this, so affected entries have to be
    removed individually. Work is spread across a few channels at a time and
    paced to reduce rate-limit pressure. Progress is logged continuously.
    """
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        log.error("Startup permission restoration skipped: guild is unavailable.")
        return 0, 0

    targets_by_channel: list[
        tuple[discord.abc.GuildChannel, list[discord.Member]]
    ] = []
    total_targets = 0

    # Categories first, then their channels. Removing category-level personal
    # denies early can restore inherited access while channel cleanup continues.
    ordered_channels = sorted(
        guild.channels,
        key=lambda item: (0 if isinstance(item, discord.CategoryChannel) else 1, item.position),
    )

    for channel in ordered_channels:
        members = [
            target
            for target in list(channel.overwrites)
            if isinstance(target, discord.Member) and not target.bot
        ]
        if members:
            targets_by_channel.append((channel, members))
            total_targets += len(members)

    log.info(
        "Startup permission restoration found %s personal overwrite(s) "
        "across %s channel/category object(s).",
        total_targets,
        len(targets_by_channel),
    )

    if not targets_by_channel:
        log.info("Startup permission restoration: nothing to repair.")
        return 0, 0

    repaired = 0
    failed = 0
    processed = 0
    counter_lock = asyncio.Lock()
    channel_semaphore = asyncio.Semaphore(3)

    async def repair_channel(
        channel: discord.abc.GuildChannel,
        members: list[discord.Member],
    ) -> None:
        nonlocal repaired, failed, processed

        async with channel_semaphore:
            for member in members:
                success = False
                try:
                    # Delete the complete personal overwrite. This makes the
                    # member inherit exactly what @everyone, their roles, the
                    # category and the channel settings grant or deny.
                    await channel.set_permissions(
                        member,
                        overwrite=None,
                        reason=(
                            "Emergency restore of original server role/category "
                            "permissions after onboarding channel locks"
                        ),
                    )
                    success = True
                except discord.Forbidden:
                    log.warning(
                        "Cannot remove personal overwrite in channel %s for member %s.",
                        channel.id,
                        member.id,
                    )
                except discord.HTTPException as exc:
                    log.warning(
                        "Failed to remove personal overwrite in channel %s for "
                        "member %s: %s",
                        channel.id,
                        member.id,
                        exc,
                    )

                async with counter_lock:
                    processed += 1
                    if success:
                        repaired += 1
                    else:
                        failed += 1

                    if processed % 25 == 0 or processed == total_targets:
                        log.info(
                            "Startup permission restoration progress: %s/%s "
                            "processed, %s repaired, %s failed.",
                            processed,
                            total_targets,
                            repaired,
                            failed,
                        )

                # Keep each channel bucket calm. discord.py also honors any
                # Retry-After response returned by Discord automatically.
                await asyncio.sleep(1.10)

    await asyncio.gather(
        *(repair_channel(channel, members) for channel, members in targets_by_channel)
    )

    log.info(
        "Startup permission restoration finished: %s repaired, %s failed.",
        repaired,
        failed,
    )
    return repaired, failed


async def onboarding_reconciliation_loop() -> None:
    try:
        while not bot.is_closed():
            await asyncio.sleep(ONBOARDING_RECONCILE_INTERVAL_SECONDS)
            try:
                await synchronize_all_members_from_reactions()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Unexpected error during onboarding safety reconciliation.")
    except asyncio.CancelledError:
        pass


async def grandfather_existing_members() -> None:
    await synchronize_all_members_from_reactions()


async def find_or_create_member_count_channel(
    guild: discord.Guild,
) -> Optional[discord.abc.GuildChannel]:
    if MEMBER_COUNT_CHANNEL_ID:
        existing = guild.get_channel(MEMBER_COUNT_CHANNEL_ID)
        if existing is not None:
            return existing

    saved_id = db.setting("member_count_channel_id")
    if saved_id and saved_id.isdigit():
        saved = guild.get_channel(int(saved_id))
        if saved is not None:
            return saved

    for channel in guild.channels:
        if channel.name.lower().startswith("members:"):
            db.set_setting("member_count_channel_id", str(channel.id))
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
        db.set_setting("member_count_channel_id", str(channel.id))
        return channel
    except discord.Forbidden:
        log.warning("Missing Manage Channels permission for member count.")
    except discord.HTTPException:
        log.exception("Could not create the member count channel.")

    return None


                                                                       
                                                                             
MEMBER_COUNT_EDIT_INTERVAL = 600.0
_member_count_edit_lock = asyncio.Lock()
_member_count_last_edit = 0.0
_member_count_pending_task: Optional[asyncio.Task] = None


async def _perform_member_count_update() -> None:
    global _member_count_last_edit

    async with _member_count_edit_lock:
        guild = bot.get_guild(GUILD_ID)
        if guild is None:
            return

        count = guild.member_count or len(guild.members)
        channel = await find_or_create_member_count_channel(guild)
        if channel is None:
            return

        new_name = MEMBER_COUNT_CHANNEL_NAME.format(count=count)
        if channel.name == new_name:
            return

        elapsed = time.monotonic() - _member_count_last_edit
        if _member_count_last_edit and elapsed < MEMBER_COUNT_EDIT_INTERVAL:
            await asyncio.sleep(MEMBER_COUNT_EDIT_INTERVAL - elapsed)

                                                                              
            guild = bot.get_guild(GUILD_ID)
            if guild is None:
                return
            count = guild.member_count or len(guild.members)
            channel = await find_or_create_member_count_channel(guild)
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
            _member_count_last_edit = time.monotonic()
        except discord.Forbidden:
            log.warning("Missing Manage Channels permission for member count.")
        except discord.HTTPException:
            log.exception("Could not update member count channel.")


async def _member_count_update_runner() -> None:
    global _member_count_pending_task
    try:
        await _perform_member_count_update()
    finally:
        _member_count_pending_task = None


async def update_member_count() -> None:
    global _member_count_pending_task

                                                                          
                                                                        
    if _member_count_pending_task is None or _member_count_pending_task.done():
        _member_count_pending_task = asyncio.create_task(
            _member_count_update_runner()
        )


async def send_welcome(member: discord.Member) -> None:
    channel: Optional[discord.TextChannel] = None

    if WELCOME_CHANNEL_ID:
        channel = await get_text_channel(WELCOME_CHANNEL_ID)

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


                                                                               
        
                                                                               

@bot.event
async def on_ready() -> None:
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(
            name="Orbital support on standby."
        ),
    )

    if not bot.ready_once:
        bot.ready_once = True

        # Do not rewrite member channel permissions or resynchronize existing
        # reaction roles on startup. Existing Discord roles and the server's
        # normal @everyone/role/category/channel permissions remain untouched.
        await update_member_count()
        await resume_giveaways()

    log.info("Logged in as %s", bot.user)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if member.guild.id != GUILD_ID or member.bot:
        return

    db.ensure_user(member.id)
    db.set_onboarding(member.id, "exempt", 0)
    db.set_onboarding(member.id, "ever_verified", 0)

    await apply_onboarding_access(member)
    await update_onboarding_dm(member)
    await send_welcome(member)
    await update_member_count()


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    if member.guild.id != GUILD_ID:
        return

    db.delete_onboarding(member.id)
    await update_member_count()


@bot.event
async def on_member_update(
    before: discord.Member,
    after: discord.Member,
) -> None:
    if after.guild.id != GUILD_ID or after.bot:
        return

                                                                           
                                                                           
                                          
    return


                                                                               
           
                                                                               

async def payload_member(
    payload: discord.RawReactionActionEvent,
) -> Optional[discord.Member]:
    guild = bot.get_guild(payload.guild_id or 0)
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


async def message_has_member_reaction(
    guild: discord.Guild,
    channel_id: int,
    message_id: int,
    emoji_key: str,
    user_id: int,
) -> Optional[bool]:
    """Return True/False when Discord could be checked, or None on API failure."""
    message = await fetch_required_message(guild, channel_id, message_id)
    if message is None:
        return None

    users = await reaction_user_ids(message, emoji_key)
    if users is None:
        return None
    return user_id in users


async def refresh_member_required_confirmations(member: discord.Member) -> None:
    """Re-read the three required checkmark messages for one member.

    Existing accepted confirmations are never revoked here. This function only
    promotes missing database fields to 1 when Discord confirms the reaction.
    """
    checks = (
        ("rules", RULES_CHANNEL, RULES_MESSAGE),
        ("booster_rules", BOOSTER_RULES_CHANNEL, BOOSTER_RULES_MESSAGE),
        ("bulletin", BULLETIN_CHANNEL, BULLETIN_MESSAGE),
    )

    for field, channel_id, message_id in checks:
        result = await message_has_member_reaction(
            member.guild,
            channel_id,
            message_id,
            CHECKMARK,
            member.id,
        )
        if result is True:
            db.set_onboarding(member.id, field, 1)


async def handle_verification_reaction(
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

    member = await payload_member(payload)
    if member is None or member.bot:
        return True

    db.ensure_user(member.id)

    # Required confirmations are permanent. A reaction removal event must never
    # revoke an already accepted onboarding step; only /reset_reactions may do so.
    if not added:
        return True

    db.set_onboarding(member.id, "exempt", 0)
    db.set_onboarding(member.id, field, 1)

    # Do not rely only on event order or an older database state. Re-read all
    # required checkmark messages for this member, then immediately repair the
    # next-channel visibility from the resulting authoritative progress.
    await refresh_member_required_confirmations(member)
    await apply_onboarding_access(member)
    return True


async def complete_role_selection_if_needed(member: discord.Member, added: bool) -> None:
    if not added or not db.has_onboarding(member.id):
        return
    db.set_onboarding(member.id, "role_selected", 1)
    await apply_onboarding_access(member)


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


async def handle_reaction_roles(
    payload: discord.RawReactionActionEvent,
    added: bool,
) -> bool:
    if payload.guild_id != GUILD_ID:
        return False

    emoji_key = custom_emoji_key(payload.emoji)

    if (
        payload.channel_id == ROLE_SELECTION_CHANNEL
        and payload.message_id == LEAGUE_MESSAGE
    ):
        if emoji_key not in LEAGUE_ROLES:
            return True
        role_id = LEAGUE_ROLES[emoji_key]

        member = await payload_member(payload)
        guild = bot.get_guild(GUILD_ID)

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
                    for resolved in [resolve_configured_role(
                        guild,
                        configured_id,
                        LEAGUE_ROLE_NAMES.get(configured_emoji, ""),
                    )]
                    if resolved is not None
                }

                remove_roles = [
                    role for role in member.roles
                    if role.id in other_roles
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

                await complete_role_selection_if_needed(member, True)

                channel = bot.get_channel(payload.channel_id)
                if isinstance(channel, discord.TextChannel):
                    try:
                        panel = await channel.fetch_message(payload.message_id)
                        for configured_emoji in LEAGUE_ROLES:
                            if configured_emoji == emoji_key:
                                continue
                            try:
                                removal_emoji = parse_emoji(configured_emoji)
                                BOT_MANAGED_REACTION_REMOVALS.add(
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

                if db.has_onboarding(member.id):
                    row = db.onboarding(member.id)
                    if not bool(row["exempt"]):
                        remaining_league = any(
                            resolve_configured_role(
                                guild,
                                configured_id,
                                LEAGUE_ROLE_NAMES.get(configured_emoji, ""),
                            ) in member.roles
                            for configured_emoji, configured_id in LEAGUE_ROLES.items()
                        )
                        if not remaining_league:
                            db.set_onboarding(member.id, "role_selected", 0)
                            db.set_onboarding(member.id, "completed", 0)
                            await apply_onboarding_access(member)

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

        member = await payload_member(payload)
        guild = bot.get_guild(GUILD_ID)
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

                db.ensure_user(member.id)
                db.set_onboarding(member.id, "platform_selected", 1)
                await apply_onboarding_access(member)

                channel = bot.get_channel(payload.channel_id)
                if isinstance(channel, discord.TextChannel):
                    try:
                        panel = await channel.fetch_message(payload.message_id)

                        selected_emoji_id = getattr(payload.emoji, "id", None)
                        selected_emoji_name = getattr(
                            payload.emoji,
                            "name",
                            str(payload.emoji),
                        ).casefold()

                        # Exactly like the league selector: the newest platform
                        # reaction wins. Remove this member from every other
                        # reaction on the platform panel, regardless of emoji
                        # name/ID configuration.
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

                            BOT_MANAGED_REACTION_REMOVALS.add(
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
                                BOT_MANAGED_REACTION_REMOVALS.discard(
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
                    db.ensure_user(member.id)
                    db.set_onboarding(member.id, "platform_selected", 0)
                    db.set_onboarding(member.id, "completed", 0)
                    await apply_onboarding_access(member)

        except discord.Forbidden:
            log.warning("Could not update platform role for %s.", member.id)
        except discord.HTTPException:
            log.exception("Could not update platform role for %s.", member.id)

        return True

    if (
        payload.channel_id == ROLE_SELECTION_CHANNEL
        and payload.message_id == NOTIFICATION_MESSAGE
    ):
        configured = NOTIFICATION_ROLES.get(emoji_key)
        if not configured:
            return True

        role_id, label = configured

        member = await payload_member(payload)
        guild = bot.get_guild(GUILD_ID)

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


@bot.event
async def on_raw_reaction_add(
    payload: discord.RawReactionActionEvent,
) -> None:
    if bot.user and payload.user_id == bot.user.id:
        return

    async with reaction_member_lock(payload.user_id):
        if await handle_verification_reaction(payload, True):
            return
        await handle_reaction_roles(payload, True)


@bot.event
async def on_raw_reaction_remove(
    payload: discord.RawReactionActionEvent,
) -> None:
    if bot.user and payload.user_id == bot.user.id:
        return

    key = reaction_removal_key(
        payload.user_id,
        payload.channel_id,
        payload.message_id,
        payload.emoji,
    )

    if key in BOT_MANAGED_REACTION_REMOVALS:
        BOT_MANAGED_REACTION_REMOVALS.discard(key)
        return

    if locked_reaction_message(payload):
        # Locked onboarding reactions are contractual confirmations. Discord
        # may still deliver a delayed remove event, but it must not alter roles,
        # access, or database state. Admins can reset them explicitly.
        return

    async with reaction_member_lock(payload.user_id):
        await handle_reaction_roles(payload, False)


                                                                               
              
                                                                               

async def automatic_unmute_log(
    guild_id: int,
    user_id: int,
    log_channel_id: int = MODERATION_LOG_CHANNEL,
) -> None:
    await asyncio.sleep(10)

    guild = bot.get_guild(guild_id)
    if guild is None or bot.user is None:
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
            "UNMUTE",
            bot.user,
            target=member,
        )
    else:
        await modlog(
            "UNMUTE",
            member,
            bot.user,
            "Mute duration expired.",
            discord.Color.green(),
            channel_id=log_channel_id,
        )


def mute_cooldown_exempt(member: discord.Member) -> bool:
    role_ids = {role.id for role in member.roles}
    return EXALTED_FOUR_ROLE in role_ids or WARDEN_ROLE in role_ids


def mute_cooldown_seconds(member: discord.Member) -> int:
    role_ids = {role.id for role in member.roles}
    if EXALTED_FOUR_ROLE in role_ids or WARDEN_ROLE in role_ids:
        return 0
    return MUTE_COOLDOWN_SECONDS


async def send_channel_cooldown(message: discord.Message, seconds: float, question: bool) -> None:
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


async def consume_shared_mute_cooldown(message: discord.Message, *, question: bool) -> bool:
    cooldown_seconds = mute_cooldown_seconds(message.author)
    if cooldown_seconds <= 0:
        return True

    now = time.monotonic()
    until = MUTE_SHARED_COOLDOWNS.get(message.author.id, 0.0)
    if until > now:
        remaining = until - now
        await delete_message(message)
        await send_channel_cooldown(message, remaining, question)
        await troll_log(
            "COOLDOWN",
            message.author,
            reason="User is still on cooldown.",
            details=f"Remaining: {format_cooldown_time(remaining)}",
        )
        return False

    MUTE_SHARED_COOLDOWNS[message.author.id] = now + cooldown_seconds
    return True


async def consume_greeting_limit(message: discord.Message) -> bool:
    if mute_cooldown_exempt(message.author):
        return True
    now = time.monotonic()
    uses = [stamp for stamp in MUTE_GREETING_USES.get(message.author.id, []) if now - stamp < MUTE_GREETING_WINDOW_SECONDS]
    if len(uses) >= MUTE_GREETING_MAX_USES:
        remaining = MUTE_GREETING_WINDOW_SECONDS - (now - min(uses))
        await delete_message(message)
        await send_channel_cooldown(message, remaining, False)
        MUTE_GREETING_USES[message.author.id] = uses
        return False
    uses.append(now)
    MUTE_GREETING_USES[message.author.id] = uses
    return True


async def handle_custom_mute(message: discord.Message) -> bool:
    if not isinstance(message.author, discord.Member):
        return False
    if not contains_mute_mention(message):
        return False

    phrase = normalize_mute_phrase(message.content)

    if phrase == "enlighten me":
        if not await consume_shared_mute_cooldown(message, question=False):
            return True
        guild = message.guild
        role = guild.get_role(ENLIGHTEN_ROLE_ID) if guild is not None else None
        if random.random() < ENLIGHTEN_ROLE_CHANCE and role is not None:
            if role not in message.author.roles:
                try:
                    await message.author.add_roles(role, reason="Rare @Mute enlighten me reward")
                except (discord.Forbidden, discord.HTTPException):
                    await reliable_message_reply(message, random.choice(ENLIGHTEN_RESPONSES))
                    return True
            await reliable_message_reply(message, "I have enlightened you.")
        else:
            await reliable_message_reply(message, random.choice(ENLIGHTEN_RESPONSES))
        return True

    if is_mute_question(message):
        if not await consume_shared_mute_cooldown(message, question=True):
            return True
        await reliable_message_reply(message, random.choice(QUESTION_RESPONSES))
        return True

    if is_only_mute_mention(message):
        if not await consume_shared_mute_cooldown(message, question=False):
            return True
        if not await consume_greeting_limit(message):
            return True
        await reliable_message_reply(message, random.choice(PING_ONLY_RESPONSES))
        return True

    if phrase not in CUSTOM_MUTE_PHRASES:
        return True
    if message.reference is None or message.reference.message_id is None:
        return True
    if not await consume_shared_mute_cooldown(message, question=False):
        return True

    if isinstance(message.reference.resolved, discord.Message):
        target_message = message.reference.resolved
    else:
        try:
            target_message = await message.channel.fetch_message(message.reference.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            await reliable_message_reply(message, "🚫 This user has cleanse stacks!")
            return True

    target = target_message.author
    if not isinstance(target, discord.Member):
        await reliable_message_reply(message, "🚫 This user has cleanse stacks!")
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
        await reliable_message_reply(message, f"🚫 {target.mention} has cleanse stacks!")
        return True

    try:
        await target.timeout(
            datetime.now(timezone.utc) + timedelta(seconds=9),
            reason=f"Reply mute by {message.author} ({message.author.id}): {phrase}",
        )
    except (discord.Forbidden, discord.HTTPException):
        await reliable_message_reply(message, f"🚫 {target.mention} has cleanse stacks!")
        return True

    await reliable_message_reply(message, f"✅ {target.mention} has been muted for 9 seconds.")
    await troll_log(
        "MUTE",
        message.author,
        target=target,
        details="Duration: 9s",
    )
    asyncio.create_task(automatic_unmute_log(message.guild.id, target.id, TROLL_CHANNEL))
    return True


async def delete_message(message: discord.Message) -> bool:
    try:
        # A tiny delay lets Discord finish the MESSAGE_CREATE/client acknowledgement
        # before the delete arrives, preventing the message from visually reappearing.
        await asyncio.sleep(0.4)
        await message.delete()
        return True
    except (discord.NotFound, discord.Forbidden):
        return False
    except discord.HTTPException:
        log.exception("Could not delete message %s.", message.id)
        return False


async def attachment_banned_term(
    message: discord.Message,
) -> Optional[str]:
    if not OCR_ENABLED:
        return None

    for attachment in message.attachments:
        extension = Path(attachment.filename).suffix.lower()

        if extension not in OCR_EXTENSIONS:
            continue
        if attachment.size > OCR_MAX_BYTES:
            continue

        try:
            image_bytes = await attachment.read()
            text = await asyncio.to_thread(run_ocr, image_bytes)
            term = find_banned_term(text)

            if term:
                return term

        except pytesseract.TesseractNotFoundError:
            log.error("Tesseract executable was not found; OCR is disabled.")
            return None
        except Exception:
            log.exception("OCR failed for attachment %s.", attachment.id)

    return None


@bot.event
async def on_message(message: discord.Message) -> None:
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

    await handle_custom_mute(message)


@bot.event
async def on_message_edit(
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
    embed.add_field(name="Before", value=(before.content or "No text")[:1024], inline=False)
    embed.add_field(name="After", value=(after.content or "No text")[:1024], inline=False)
    embed.add_field(name="Message", value=after.jump_url, inline=False)

    await send_embed(EDIT_LOG_CHANNEL_ID, embed)


@bot.event
async def on_message_delete(message: discord.Message) -> None:
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
    embed.add_field(name="Content", value=(message.content or "No text")[:1024], inline=False)

    if message.attachments:
        names = "\n".join(item.filename for item in message.attachments)
        embed.add_field(name="Attachments", value=names[:1024], inline=False)

    await send_embed(DELETE_LOG_CHANNEL_ID, embed)


                                                                               
                
                                                                               

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


@bot.tree.error
async def app_command_error(
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

    if isinstance(original, discord.NotFound) and getattr(original, "code", None) == 10062:
        log.warning("Discord interaction expired before the bot could respond.")
        return

    log.exception("Unhandled slash-command error.", exc_info=original)
    try:
        await reply_ephemeral(interaction, "An unexpected error occurred.")
    except discord.NotFound:
        log.warning("Could not send the error response because the interaction expired.")


                                                                               
                     
                                                                               

@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    member="The member to ban",
    reason="The required reason for the ban",
    delete_message_days="Message history to delete, from 0 to 7 days",
)
@staff_only()
async def ban(
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


@bot.tree.command(name="mute", description="Mute a member for a duration.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    member="The member to mute",
    duration="Examples: 30s, 10m, 2h, 3d, or 1w",
    reason="The required reason for the mute",
)
@staff_only()
async def mute(
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


@bot.tree.command(name="unmute", description="Remove a member's timeout.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    member="The member to unmute",
    reason="The reason for removing the mute",
)
@staff_only()
async def unmute(
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


@bot.tree.command(name="warn", description="Add a warning to a member.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    member="The member to warn",
    reason="The required reason for the warning",
)
@staff_only()
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str,
) -> None:
    allowed, error = can_moderate(interaction.user, member)

    if not allowed:
        await reply_ephemeral(interaction, error)
        return

    warning_id = db.add_warning(
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


@bot.tree.command(name="warnings", description="Show a member's warnings.")
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    member="The member whose warnings should be shown",
)
@staff_only()
async def warnings_command(
    interaction: discord.Interaction,
    member: discord.Member,
) -> None:
    rows = db.warnings(member.id)

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


@bot.tree.command(
    name="clearwarnings",
    description="Delete all warnings for a member.",
)
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    member="The member whose warnings should be deleted",
    reason="The required reason for clearing warnings",
)
@staff_only()
async def clearwarnings(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str,
) -> None:
    count = db.clear_warnings(member.id)

    await modlog(
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


                                                                               
                
                                                                               

@bot.tree.command(
    name="setup_verification_reactions",
    description="Add checkmarks to the existing onboarding messages.",
)
@app_commands.guilds(GUILD_OBJECT)
@staff_only()
async def setup_verification_reactions(
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
        channel = await get_text_channel(channel_id)

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


@bot.tree.command(
    name="setup_league_roles",
    description="Create the league reaction-role panel in this channel.",
)
@app_commands.guilds(GUILD_OBJECT)
@staff_only()
async def setup_league_roles(
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

    db.set_setting("league_message", str(message.id))

    await interaction.followup.send(
        f"League panel created. Message ID: {message.id}",
        ephemeral=True,
    )


@bot.tree.command(
    name="setup_notification_roles",
    description="Create the notification reaction-role panel in this channel.",
)
@app_commands.guilds(GUILD_OBJECT)
@staff_only()
async def setup_notification_roles(
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

    db.set_setting("notification_message", str(message.id))

    await interaction.followup.send(
        f"Notification panel created. Message ID: {message.id}",
        ephemeral=True,
    )


@bot.tree.command(
    name="refresh_onboarding",
    description="Show the current onboarding behavior.",
)
@app_commands.guilds(GUILD_OBJECT)
@staff_only()
async def refresh_onboarding(
    interaction: discord.Interaction,
) -> None:
    await interaction.response.send_message(
        "Existing members are exempt. Onboarding is applied automatically only when a new member joins.",
        ephemeral=True,
    )


                                                                               
           
                                                                               

async def finish_giveaway(message_id: int) -> None:
    row = next(
        (
            item for item in db.active_giveaways()
            if int(item["message_id"]) == message_id
        ),
        None,
    )

    if row is None:
        return

    guild = bot.get_guild(int(row["guild_id"]))
    channel = (
        guild.get_channel(int(row["channel_id"]))
        if guild is not None
        else None
    )

    if not isinstance(channel, discord.TextChannel):
        db.end_giveaway(message_id)
        return

    try:
        message = await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        db.end_giveaway(message_id)
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

    db.end_giveaway(message_id)
    bot.giveaway_tasks.pop(message_id, None)


async def giveaway_timer(
    message_id: int,
    ends_at: datetime,
) -> None:
    delay = max(
        0,
        (ends_at - datetime.now(timezone.utc)).total_seconds(),
    )
    await asyncio.sleep(delay)
    await finish_giveaway(message_id)


async def resume_giveaways() -> None:
    for row in db.active_giveaways():
        ends_at = datetime.fromisoformat(str(row["ends_at"]))
        message_id = int(row["message_id"])

        bot.giveaway_tasks[message_id] = asyncio.create_task(
            giveaway_timer(message_id, ends_at)
        )


@bot.tree.command(
    name="giveaway",
    description="Start a giveaway in the current channel.",
)
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    duration="Examples: 10m, 2h, 3d, or 1w",
    winners="Number of winners",
    prize="The giveaway prize",
)
@staff_only()
async def giveaway(
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

    db.add_giveaway(
        message.id,
        message.channel.id,
        interaction.user.id,
        prize,
        winners,
        ends_at,
    )

    bot.giveaway_tasks[message.id] = asyncio.create_task(
        giveaway_timer(message.id, ends_at)
    )

    await interaction.edit_original_response(
        content=f"Giveaway created. Message ID: {message.id}"
    )


@bot.tree.command(
    name="endgiveaway",
    description="End a giveaway immediately.",
)
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    message_id="The giveaway message ID",
)
@staff_only()
async def endgiveaway(
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

    task = bot.giveaway_tasks.pop(numeric_id, None)
    if task is not None:
        task.cancel()

    await interaction.response.defer(ephemeral=True)
    await finish_giveaway(numeric_id)
    await interaction.followup.send(
        "Giveaway ended.",
        ephemeral=True,
    )


@bot.tree.command(
    name="rerollgiveaway",
    description="Pick new winner(s) for a giveaway.",
)
@app_commands.guilds(GUILD_OBJECT)
@app_commands.describe(
    message_id="The giveaway message ID",
    winners="Number of winners",
)
@staff_only()
async def rerollgiveaway(
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


@bot.tree.command(
    name="membercount",
    description="Show the current server member count.",
)
@app_commands.guilds(GUILD_OBJECT)
async def membercount(
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


                                                                               
       
                                                                               

def main() -> None:
    if TESSERACT_COMMAND:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_COMMAND
    else:
        log.warning("Tesseract is not installed; OCR image scanning is disabled.")

    token = BOT_TOKEN.strip()

    if not token or token == "PASTE_YOUR_DISCORD_BOT_TOKEN_HERE":
        raise RuntimeError(
            'Set BOT_TOKEN in the Wispbyte .env/environment variables.'
        )

    bot.run(token)


if __name__ == "__main__":
    main()