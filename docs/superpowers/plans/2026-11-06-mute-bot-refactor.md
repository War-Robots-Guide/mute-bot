# War Robots Guide Mute Bot Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the monolithic 3,616-line `Mute.py` Discord bot into a modular, tested `mute_bot` Python package with Cogs and domain services in `https://github.com/War-Robots-Guide/mute-bot.git`.

**Architecture:** Pure domain logic (SQLite persistence, duration/emoji formatting, moderation hierarchy checks, homoglyph/OCR AutoMod filtering, and `@Mute` phrase/cooldown handling) lives in `mute_bot/database.py` and `mute_bot/services/`. Discord I/O (slash commands and event listeners) lives in four `discord.py` Cogs (`ModerationCog`, `InteractionsCog`, `OnboardingCog`, `GiveawaysCog`) loaded by `MuteBot` in `mute_bot/bot.py`, with `Mute.py` preserved as a thin entrypoint wrapper for hosting compatibility.

**Tech Stack:** Python `>=3.11`, `discord.py >=2.3`, `Pillow`, `pytesseract`, `python-dotenv`, `sqlite3`, `pytest`, `pytest-asyncio`.

**Spec:** `docs/superpowers/specs/2026-11-06-mute-bot-refactor-design.md`

## Global Constraints

- Default SQLite database path: `Path(__file__).resolve().parent.parent / "mute_bot.sqlite3"` (`mute_bot.sqlite3` in repo root).
- Guild & Role IDs: `GUILD_ID = 1197548660188254228`, `EXALTED_FOUR_ROLE = 1373799510907555900`, `WARDEN_ROLE = 1517284495693316287`, `CREDIBLE_SOURCE_ROLE = 1517251235927953559`, `ENLIGHTENED_VISITOR_ROLE = 1531553090660990999`, `VISITOR_ROLE = 1385042493740945478`, `ENLIGHTEN_ROLE_ID = 1466144906136387869`.
- Channel & Message IDs: `NAILBITING_CHANNEL = 1522577153882067014`, `MODERATION_LOG_CHANNEL = 1517479326910644414`, `TROLL_CHANNEL = 1537492053770903552`, `RULES_CHANNEL = 1517238642685378570`, `RULES_MESSAGE = 1517239514131730462`, `BOOSTER_RULES_CHANNEL = RULES_CHANNEL`, `BOOSTER_RULES_MESSAGE = 1525161622627418175`, `BULLETIN_CHANNEL = 1466121899741286698`, `BULLETIN_MESSAGE = 1531792133474877592`, `ROLE_SELECTION_CHANNEL = 1517237717459537991`, `LEAGUE_MESSAGE = 1531555776873758814`, `NOTIFICATION_MESSAGE = 1531557718543044741`, `PLATFORM_MESSAGE = 1534571044101161242`, `DELETE_LOG_CHANNEL_ID = MODERATION_LOG_CHANNEL`, `EDIT_LOG_CHANNEL_ID = 0`, `AUTOMOD_LOG_CHANNEL_ID = 0`, `WELCOME_CHANNEL_ID = 0`, `MEMBER_COUNT_CHANNEL_ID = 0`.
- Importing any module in `mute_bot` or `Mute.py` must not raise `RuntimeError` when `BOT_TOKEN` is unset; token validation occurs only inside `main()`.
- Root `Mute.py` must remain executable via `python Mute.py` and delegate to `mute_bot.main:main`.

## Review Focus

1. **Dynamic SQL column whitelist (`Database.set_onboarding`):** Passing an unwhitelisted field name (e.g., `"rules = 1; DROP TABLE onboarding; --"`) must raise `ValueError` before touching SQLite.
2. **Duration boundary and malformed input (`parse_duration`):** Inputs with trailing/embedded invalid tokens (`"10m5x"`), zero duration (`"0s"`), or durations exceeding Discord's 28-day timeout ceiling (`"29d"`, `"4w1s"`) must raise `ValueError`.
3. **AutoMod substring false positives vs. obfuscated slurs (`find_banned_term`):** `"rape"` must match `"rape"` and `"raped"` (including spaced/leet variants like `"r.a.p.e.d"`), but must not match `"trapped"`, `"scraped"`, `"draped"`, or `"grape"`; zero-width characters and ASCII art `"|/\\|"` for `"n"` must be caught.
4. **Mention boundary and staff cooldown exemption (`contains_mute_mention`, `CooldownTracker`):** `@mute` inside an email or longer handle (`"test@mute.com"`, `"@mutes"`) must not trigger the bot, while `<@!BOT_ID>` and standalone `@Mute` do; staff roles (`EXALTED_FOUR_ROLE`, `WARDEN_ROLE`) must bypass both the 180s shared cooldown and the 2-per-30s greeting limit.
5. **Message pipeline ordering & reaction-role self-removal loop (`InteractionsCog`, `OnboardingCog`):** A message containing both a banned term and `@Mute enlighten me` must be deleted by AutoMod without sending an `@Mute` reply; bot-initiated reaction removals when switching league/platform roles must be ignored by `on_raw_reaction_remove` so the user's newly granted role or onboarding state is not stripped.

---

### Task 1: Project Scaffolding, Configuration, Static Data, and SQLite Database

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `mute_bot/__init__.py`
- Create: `mute_bot/config.py`
- Create: `mute_bot/data/__init__.py`
- Create: `mute_bot/data/responses.py`
- Create: `mute_bot/database.py`
- Test: `tests/__init__.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: standard library (`sqlite3`, `pathlib.Path`, `datetime`, `os`, `shutil`).
- Produces:
  - `mute_bot.config`: all Guild/Role/Channel/Message constants, `DB_PATH`, `OCR_ENABLED`, `OCR_MAX_BYTES`, `OCR_EXTENSIONS`, `CHECKMARK`, `GIVEAWAY_REACTION`, `LEAGUE_ROLES`, `LEAGUE_ROLE_NAMES`, `NOTIFICATION_ROLES`, `PLATFORM_ROLES`, `ENLIGHTEN_ROLE_CHANCE`, `MUTE_COOLDOWN_SECONDS`, `MUTE_GREETING_WINDOW_SECONDS`, `MUTE_GREETING_MAX_USES`, `MEMBER_COUNT_CHANNEL_NAME`, `AUTO_CREATE_MEMBER_COUNT_CHANNEL`, `MEMBER_COUNT_EDIT_INTERVAL`, `ONBOARDING_RECONCILE_INTERVAL_SECONDS`.
  - `mute_bot.data.responses`: `CUSTOM_MUTE_PHRASES: set[str]`, `PING_ONLY_RESPONSES: tuple[str, ...]`, `QUESTION_RESPONSES: tuple[str, ...]`, `ENLIGHTEN_RESPONSES: tuple[str, ...]`, `BANNED_TERMS: tuple[str, ...]`, `CHAR_EQ: dict[str, str]`.
  - `mute_bot.database.Database(path: Path = DB_PATH, guild_id: int = GUILD_ID)` with methods:
    - `connect() -> sqlite3.Connection`
    - `initialize() -> None`
    - `ensure_user(user_id: int) -> None`
    - `has_onboarding(user_id: int) -> bool`
    - `mark_existing_member_completed(user_id: int) -> None`
    - `onboarding(user_id: int) -> sqlite3.Row`
    - `set_onboarding(user_id: int, field: str, value: object) -> None`
    - `delete_onboarding(user_id: int) -> None`
    - `setting(key: str) -> Optional[str]`
    - `set_setting(key: str, value: str) -> None`
    - `add_warning(user_id: int, moderator_id: int, reason: str) -> int`
    - `warnings(user_id: int) -> list[sqlite3.Row]`
    - `clear_warnings(user_id: int) -> int`
    - `add_giveaway(message_id: int, channel_id: int, host_id: int, prize: str, winners: int, ends_at: datetime) -> None`
    - `active_giveaways() -> list[sqlite3.Row]`
    - `end_giveaway(message_id: int) -> None`

- [ ] **Step 1: Initialize Git repository, `.venv`, and project metadata (`pyproject.toml`, `requirements.txt`, `.gitignore`, `.env.example`)**

Initialize git in `/home/lihaowang/Documents/code/warrobotsguide/mute-bot` with remote `origin` set to `https://github.com/War-Robots-Guide/mute-bot.git`, create `.venv` with `--system-site-packages`, and install `discord.py`, `pytesseract`, and `python-dotenv` into `.venv`.

- [ ] **Step 2: Write the failing database and config tests in `tests/test_database.py`**

```python
from datetime import datetime, timezone
import sqlite3
import pytest
from mute_bot.config import GUILD_ID, LEAGUE_ROLES, PLATFORM_ROLES, NOTIFICATION_ROLES
from mute_bot.data.responses import BANNED_TERMS, CUSTOM_MUTE_PHRASES, ENLIGHTEN_RESPONSES, QUESTION_RESPONSES
from mute_bot.database import Database


def test_config_and_responses_preserved() -> None:
    assert GUILD_ID == 1197548660188254228
    assert len(LEAGUE_ROLES) == 8
    assert len(PLATFORM_ROLES) == 4
    assert len(NOTIFICATION_ROLES) == 2
    assert "enlighten me" not in CUSTOM_MUTE_PHRASES
    assert "get him" in CUSTOM_MUTE_PHRASES
    assert len(ENLIGHTEN_RESPONSES) == 50
    assert len(QUESTION_RESPONSES) == 70
    assert BANNED_TERMS == ("hitler", "rape", "faggot", "nigga", "negro", "negra", "kys")


def test_onboarding_crud_and_field_whitelist(tmp_path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    assert not db.has_onboarding(42)
    row = db.onboarding(42)
    assert db.has_onboarding(42)
    assert row["rules"] == 0
    db.set_onboarding(42, "rules", 1)
    assert db.onboarding(42)["rules"] == 1

    with pytest.raises(ValueError, match="invalid_column"):
        db.set_onboarding(42, "invalid_column", 1)

    db.delete_onboarding(42)
    assert not db.has_onboarding(42)


def test_schema_migration_adds_missing_onboarding_columns(tmp_path) -> None:
    db_file = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "CREATE TABLE onboarding (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (guild_id, user_id))"
        )
    db = Database(db_file)
    row = db.onboarding(99)
    assert row["platform_selected"] == 0
    assert row["ever_verified"] == 0


def test_warnings_settings_and_giveaways(tmp_path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    assert db.setting("league_message") is None
    db.set_setting("league_message", "12345")
    assert db.setting("league_message") == "12345"

    w1 = db.add_warning(100, 200, "First warning")
    w2 = db.add_warning(100, 201, "Second warning")
    assert w2 > w1
    warnings = db.warnings(100)
    assert [w["reason"] for w in warnings] == ["First warning", "Second warning"]
    assert db.clear_warnings(100) == 2
    assert db.warnings(100) == []

    ends = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
    db.add_giveaway(555, 666, 777, "Prime Sword", 2, ends)
    active = db.active_giveaways()
    assert len(active) == 1
    assert active[0]["prize"] == "Prime Sword"
    db.end_giveaway(555)
    assert db.active_giveaways() == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_database.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mute_bot.config'`

- [ ] **Step 4: Implement `mute_bot/config.py`, `mute_bot/data/responses.py`, and `mute_bot/database.py`**

Move all constants and response tuples verbatim from `Mute.py` lines 32–340 into `mute_bot/config.py` and `mute_bot/data/responses.py` (without raising `RuntimeError` if `BOT_TOKEN` is missing at import time), and implement `Database` in `mute_bot/database.py` matching `Mute.py` lines 358–636 with parameterized `guild_id: int = GUILD_ID`.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_database.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements.txt .gitignore .env.example mute_bot/__init__.py mute_bot/config.py mute_bot/data/__init__.py mute_bot/data/responses.py mute_bot/database.py tests/__init__.py tests/test_database.py
git commit -m "feat: add project config, static response data, and SQLite database layer"
```

---

### Task 2: Formatting, Permissions, Discord Helpers, and Logging Services

**Files:**
- Create: `mute_bot/services/__init__.py`
- Create: `mute_bot/services/formatting.py`
- Create: `mute_bot/services/permissions.py`
- Create: `mute_bot/services/discord_helpers.py`
- Create: `mute_bot/services/logging_service.py`
- Test: `tests/test_formatting.py`
- Test: `tests/test_permissions.py`

**Interfaces:**
- Consumes: `mute_bot.config` (`EXALTED_FOUR_ROLE`, `WARDEN_ROLE`, `CREDIBLE_SOURCE_ROLE`, `ENLIGHTEN_ROLE_ID`, `MODERATION_LOG_CHANNEL`, `TROLL_CHANNEL`, `AUTOMOD_LOG_CHANNEL_ID`).
- Produces:
  - `mute_bot.services.formatting`:
    - `format_cooldown_time(seconds: float) -> str`
    - `identity(user: discord.abc.User) -> str`
    - `ordinal(number: int) -> str`
    - `parse_duration(text: str) -> tuple[timedelta, str]`
    - `custom_emoji_key(emoji: discord.PartialEmoji | discord.Emoji | str) -> str`
    - `parse_emoji(value: str) -> str | discord.PartialEmoji`
  - `mute_bot.services.permissions`:
    - `staff(member: discord.Member) -> bool`
    - `reply_mute_level(member: discord.Member) -> int`
    - `can_moderate(moderator: discord.Member, target: discord.Member) -> tuple[bool, str]`
    - `staff_only() -> Callable[[T], T]`
    - `admin_only() -> Callable[[T], T]`
  - `mute_bot.services.discord_helpers`:
    - `reliable_message_reply(message: discord.Message, content: str) -> None`
    - `reply_ephemeral(interaction: discord.Interaction, content: str) -> None`
    - `delete_message(message: discord.Message) -> bool`
    - `get_text_channel(bot: commands.Bot, channel_id: int) -> Optional[discord.TextChannel]`
    - `send_embed(bot: commands.Bot, channel_id: int, embed: discord.Embed) -> None`
    - `resolve_configured_role(guild: discord.Guild, role_id: int, role_name: str) -> Optional[discord.Role]`
  - `mute_bot.services.logging_service`:
    - `modlog(bot: commands.Bot, action: str, target: discord.abc.User, moderator: discord.abc.User, reason: str, color: discord.Color, details: Optional[str] = None, channel_id: int = MODERATION_LOG_CHANNEL) -> None`
    - `troll_log(bot: commands.Bot, action: str, user: discord.abc.User, *, target: Optional[discord.abc.User] = None, reason: Optional[str] = None, details: Optional[str] = None) -> None`
    - `automod_log(bot: commands.Bot, member: discord.Member, channel: discord.abc.GuildChannel | discord.Thread, reason: str, content: str) -> None`

- [ ] **Step 1: Write the failing tests in `tests/test_formatting.py` and `tests/test_permissions.py`**

```python
# tests/test_formatting.py
from datetime import timedelta
import discord
import pytest
from mute_bot.services.formatting import (
    custom_emoji_key,
    format_cooldown_time,
    ordinal,
    parse_duration,
    parse_emoji,
)


def test_format_cooldown_time() -> None:
    assert format_cooldown_time(0.2) == "1s"
    assert format_cooldown_time(59.1) == "60s" or format_cooldown_time(59.0) == "59s"
    assert format_cooldown_time(60) == "1m"
    assert format_cooldown_time(125) == "2m 5s"


def test_ordinal() -> None:
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(3) == "3rd"
    assert ordinal(4) == "4th"
    assert ordinal(11) == "11th"
    assert ordinal(12) == "12th"
    assert ordinal(13) == "13th"
    assert ordinal(21) == "21st"
    assert ordinal(112) == "112th"


def test_parse_duration_valid_and_invalid() -> None:
    delta, label = parse_duration("1h 30m")
    assert delta == timedelta(hours=1, minutes=30)
    assert label == "1 hour, 30 minutes"

    delta_single, label_single = parse_duration("1s")
    assert delta_single == timedelta(seconds=1)
    assert label_single == "1 second"

    for invalid in ("", "10m5x", "0s", "29d", "4w1s", "abc"):
        with pytest.raises(ValueError):
            parse_duration(invalid)


def test_emoji_helpers() -> None:
    assert custom_emoji_key("✅") == "✅"
    assert parse_emoji("✅") == "✅"
    partial = parse_emoji("league_champion:1524798134184837272")
    assert isinstance(partial, discord.PartialEmoji)
    assert partial.name == "league_champion"
    assert partial.id == 1524798134184837272
    assert custom_emoji_key(partial) == "league_champion:1524798134184837272"
```

```python
# tests/test_permissions.py
from types import SimpleNamespace
from mute_bot.config import (
    CREDIBLE_SOURCE_ROLE,
    ENLIGHTEN_ROLE_ID,
    EXALTED_FOUR_ROLE,
    WARDEN_ROLE,
)
from mute_bot.services.permissions import can_moderate, reply_mute_level, staff


def _make_member(member_id: int, role_ids: list[int], top_role_pos: int = 1, guild=None):
    roles = [SimpleNamespace(id=rid) for rid in role_ids]
    return SimpleNamespace(
        id=member_id,
        roles=roles,
        top_role=top_role_pos,
        guild=guild,
    )


def test_staff_and_reply_mute_levels() -> None:
    assert staff(_make_member(1, [EXALTED_FOUR_ROLE]))
    assert staff(_make_member(2, [WARDEN_ROLE]))
    assert not staff(_make_member(3, [CREDIBLE_SOURCE_ROLE]))

    assert reply_mute_level(_make_member(1, [EXALTED_FOUR_ROLE])) == 4
    assert reply_mute_level(_make_member(2, [WARDEN_ROLE])) == 3
    assert reply_mute_level(_make_member(3, [CREDIBLE_SOURCE_ROLE])) == 2
    assert reply_mute_level(_make_member(4, [ENLIGHTEN_ROLE_ID])) == 1
    assert reply_mute_level(_make_member(5, [])) == 0


def test_can_moderate_hierarchy_and_protections() -> None:
    guild = SimpleNamespace(owner_id=999, me=SimpleNamespace(top_role=50))
    mod = _make_member(10, [WARDEN_ROLE], top_role_pos=30, guild=guild)
    regular = _make_member(20, [], top_role_pos=5, guild=guild)
    other_staff = _make_member(30, [WARDEN_ROLE], top_role_pos=10, guild=guild)
    owner = _make_member(999, [], top_role_pos=100, guild=guild)
    higher_role_user = _make_member(40, [], top_role_pos=40, guild=guild)
    above_bot_user = _make_member(50, [], top_role_pos=60, guild=guild)
    admin_owner = _make_member(999, [EXALTED_FOUR_ROLE], top_role_pos=100, guild=guild)

    assert can_moderate(mod, regular) == (True, "")
    assert can_moderate(mod, mod) == (False, "You cannot moderate yourself.")
    assert can_moderate(mod, owner) == (False, "The server owner cannot be moderated.")
    assert can_moderate(admin_owner, other_staff) == (False, "Staff members cannot be targeted.")
    assert can_moderate(mod, higher_role_user) == (False, "Your role must be above the target's role.")
    assert can_moderate(admin_owner, above_bot_user) == (False, "My role must be above the target's role.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_formatting.py tests/test_permissions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mute_bot.services'`

- [ ] **Step 3: Implement `formatting.py`, `permissions.py`, `discord_helpers.py`, and `logging_service.py`**

Extract the formatting, permission check, Discord message/channel/role helper, and embed logging functions from `Mute.py` lines 645–1061 and 2736–2890, passing `bot: commands.Bot` explicitly to `get_text_channel`, `send_embed`, `modlog`, `troll_log`, and `automod_log`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_formatting.py tests/test_permissions.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add mute_bot/services/ tests/test_formatting.py tests/test_permissions.py
git commit -m "feat: extract formatting, permission, Discord helper, and logging services"
```

---

### Task 3: AutoMod Text Normalization, Homoglyph/Leetspeak Filter, and OCR Service

**Files:**
- Create: `mute_bot/services/automod.py`
- Test: `tests/test_automod.py`

**Interfaces:**
- Consumes: `mute_bot.config` (`OCR_ENABLED`, `OCR_EXTENSIONS`, `OCR_MAX_BYTES`), `mute_bot.data.responses` (`BANNED_TERMS`, `CHAR_EQ`).
- Produces:
  - `build_banned_patterns() -> list[tuple[str, re.Pattern[str]]]`
  - `BANNED_PATTERNS: list[tuple[str, re.Pattern[str]]]`
  - `normalize_filter_text(text: str) -> str`
  - `find_banned_term(text: str) -> Optional[str]`
  - `preprocess_ocr(image_bytes: bytes) -> Image.Image`
  - `run_ocr(image_bytes: bytes, *, ocr_enabled: Optional[bool] = None) -> str`
  - `attachment_banned_term(message: discord.Message, *, ocr_enabled: Optional[bool] = None) -> Optional[str]`

- [ ] **Step 1: Write the failing AutoMod and OCR tests in `tests/test_automod.py`**

```python
import io
from PIL import Image
from mute_bot.services.automod import (
    find_banned_term,
    normalize_filter_text,
    preprocess_ocr,
)


def test_find_banned_term_matches_exact_leet_and_homoglyphs() -> None:
    assert find_banned_term("hitler") == "hitler"
    assert find_banned_term("h!7l3r") == "hitler"
    assert find_banned_term("rape") == "rape"
    assert find_banned_term("raped") == "rape"
    assert find_banned_term("r.a.p.e.d") == "rape"
    assert find_banned_term("k.y.s") == "kys"
    assert find_banned_term("n\u200bi\u200bg\u200bg\u200ba") == "nigga"
    assert find_banned_term("|/\\|1gg@") == "nigga"


def test_find_banned_term_avoids_false_positives() -> None:
    for safe_text in (
        "I got trapped in center beacon",
        "he scraped by with 10 HP",
        "draped in gold",
        "grape juice",
        "therapist",
        "skyscraper",
        "normal War Robots discussion",
    ):
        assert find_banned_term(safe_text) is None, f"False positive on: {safe_text}"


def test_normalize_filter_text_strips_combining_and_zero_width() -> None:
    assert normalize_filter_text("h\u0301i\u200bt") == "hit"
    assert normalize_filter_text("/\\") == "n"


def test_preprocess_ocr_upscales_small_images_to_grayscale() -> None:
    img = Image.new("RGB", (300, 150), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    processed = preprocess_ocr(buf.getvalue())
    assert processed.mode == "L"
    assert processed.size == (900, 450)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_automod.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mute_bot.services.automod'`

- [ ] **Step 3: Implement `mute_bot/services/automod.py`**

Implement `build_banned_patterns`, `BANNED_PATTERNS`, `normalize_filter_text`, `find_banned_term`, `preprocess_ocr`, `run_ocr`, and `attachment_banned_term` from `Mute.py` lines 847–950 and 2750–2778.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_automod.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add mute_bot/services/automod.py tests/test_automod.py
git commit -m "feat: extract AutoMod text filter and OCR preprocessing service"
```

---

### Task 4: `@Mute` Chat Parsing & Cooldown Service

**Files:**
- Create: `mute_bot/services/mute_chat.py`
- Test: `tests/test_mute_chat.py`

**Interfaces:**
- Consumes: `mute_bot.config` (`EXALTED_FOUR_ROLE`, `WARDEN_ROLE`, `MUTE_COOLDOWN_SECONDS`, `MUTE_GREETING_WINDOW_SECONDS`, `MUTE_GREETING_MAX_USES`).
- Produces:
  - `normalize_mute_phrase(content: str, bot_user_id: Optional[int] = None) -> str`
  - `contains_mute_mention(message: discord.Message, bot_user_id: Optional[int] = None) -> bool`
  - `is_only_mute_mention(content: str, bot_user_id: Optional[int] = None) -> bool`
  - `mute_question_text(content: str, bot_user_id: Optional[int] = None) -> str`
  - `is_mute_question(message: discord.Message, bot_user_id: Optional[int] = None) -> bool`
  - `mute_cooldown_exempt(member: discord.Member) -> bool`
  - `mute_cooldown_seconds(member: discord.Member) -> int`
  - `CooldownTracker`:
    - `check_shared_cooldown(member: discord.Member, now: Optional[float] = None) -> tuple[bool, float]`
    - `check_greeting_limit(member: discord.Member, now: Optional[float] = None) -> tuple[bool, float]`

- [ ] **Step 1: Write the failing tests in `tests/test_mute_chat.py`**

```python
from types import SimpleNamespace
from mute_bot.config import EXALTED_FOUR_ROLE, WARDEN_ROLE
from mute_bot.services.mute_chat import (
    CooldownTracker,
    contains_mute_mention,
    is_mute_question,
    is_only_mute_mention,
    normalize_mute_phrase,
)


def _msg(content: str, raw_mentions: list[int] | None = None):
    return SimpleNamespace(content=content, raw_mentions=raw_mentions or [])


def _member(user_id: int, role_ids: list[int] | None = None):
    return SimpleNamespace(
        id=user_id,
        roles=[SimpleNamespace(id=r) for r in (role_ids or [])],
    )


def test_mute_phrase_and_mention_parsing() -> None:
    bot_id = 123456
    assert normalize_mute_phrase("<@!123456> Enlighten Me!!!", bot_id) == "enlighten me"
    assert normalize_mute_phrase("@Mute get him.", bot_id) == "get him"

    assert contains_mute_mention(_msg("hello <@123456>", [bot_id]), bot_id)
    assert contains_mute_mention(_msg("hey @Mute what's up"), bot_id)
    assert not contains_mute_mention(_msg("email me at user@mute.com or @mutes"), bot_id)

    assert is_only_mute_mention("<@123456> ?!.", bot_id)
    assert is_only_mute_mention("@mute", bot_id)
    assert not is_only_mute_mention("@mute hi", bot_id)

    assert is_mute_question(_msg("<@123456> is pathfinder good?", [bot_id]), bot_id)
    assert not is_mute_question(_msg("is pathfinder good?"), bot_id)


def test_cooldown_tracker_enforces_and_exempts_staff() -> None:
    tracker = CooldownTracker()
    normal = _member(10)
    staff_member = _member(20, [WARDEN_ROLE])

    allowed, rem = tracker.check_shared_cooldown(normal, now=100.0)
    assert allowed and rem == 0.0

    allowed2, rem2 = tracker.check_shared_cooldown(normal, now=150.0)
    assert not allowed2 and rem2 == 130.0

    allowed3, _ = tracker.check_shared_cooldown(normal, now=281.0)
    assert allowed3

    # Staff are always exempt from shared cooldown and greeting limits
    assert tracker.check_shared_cooldown(staff_member, now=100.0) == (True, 0.0)
    assert tracker.check_shared_cooldown(staff_member, now=101.0) == (True, 0.0)


def test_greeting_rate_limit_window() -> None:
    tracker = CooldownTracker()
    normal = _member(10)

    assert tracker.check_greeting_limit(normal, now=10.0) == (True, 0.0)
    assert tracker.check_greeting_limit(normal, now=20.0) == (True, 0.0)
    allowed, rem = tracker.check_greeting_limit(normal, now=25.0)
    assert not allowed and rem == 15.0

    # After the 30s window from first use expires
    assert tracker.check_greeting_limit(normal, now=41.0) == (True, 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_mute_chat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mute_bot.services.mute_chat'`

- [ ] **Step 3: Implement `mute_bot/services/mute_chat.py`**

Implement the pure `@Mute` mention/phrase/question functions from `Mute.py` lines 755–830 and `CooldownTracker` encapsulating `shared_cooldowns: dict[int, float]` and `greeting_uses: dict[int, list[float]]` from lines 2564–2636. Note: for `@mute` text matching, use `r"(?<![\w@])@mute(?!\w)"` so `"user@mute.com"` is not matched as a mention.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_mute_chat.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add mute_bot/services/mute_chat.py tests/test_mute_chat.py
git commit -m "feat: add @Mute message parsing and CooldownTracker service"
```

---

### Task 5: Feature Cogs, `MuteBot` Core, Entrypoints (`Mute.py` & `mute_bot/main.py`), and Documentation

**Files:**
- Create: `mute_bot/cogs/__init__.py`
- Create: `mute_bot/cogs/moderation.py`
- Create: `mute_bot/cogs/interactions.py`
- Create: `mute_bot/cogs/onboarding.py`
- Create: `mute_bot/cogs/giveaways.py`
- Create: `mute_bot/bot.py`
- Create: `mute_bot/main.py`
- Modify: `Mute.py`
- Create: `README.md`
- Test: `tests/test_cogs.py`

**Interfaces:**
- Consumes: `mute_bot.config`, `mute_bot.data.responses`, `mute_bot.database.Database`, `mute_bot.services.*`.
- Produces:
  - `mute_bot.cogs.moderation.ModerationCog(bot: MuteBot)`: `/ban`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/clearwarnings`, `on_message_edit`, `on_message_delete`.
  - `mute_bot.cogs.interactions.InteractionsCog(bot: MuteBot)`: `on_message` (runs `find_banned_term` -> `attachment_banned_term` -> `handle_custom_mute`), `handle_custom_mute`, `automatic_unmute_log`.
  - `mute_bot.cogs.onboarding.OnboardingCog(bot: MuteBot)`: `on_member_join`, `on_member_remove`, `on_raw_reaction_add`, `on_raw_reaction_remove`, `update_member_count`, `/setup_verification_reactions`, `/setup_league_roles`, `/setup_notification_roles`, `/refresh_onboarding`, `/membercount`.
  - `mute_bot.cogs.giveaways.GiveawaysCog(bot: MuteBot)`: `/giveaway`, `/endgiveaway`, `/rerollgiveaway`, `resume_giveaways`, `finish_giveaway`.
  - `mute_bot.bot.MuteBot(db: Optional[Database] = None)`: `commands.Bot` subclass registering all four cogs in `setup_hook()`, copying global commands to `GUILD_OBJECT` and syncing the command tree, handling `tree.on_error`, and setting custom status `"Orbital support on standby."` in `on_ready()`.
  - `mute_bot.main.main() -> None` and `Mute.py` delegating to `main()`.

- [ ] **Step 1: Write the failing cog and bot integration tests in `tests/test_cogs.py`**

```python
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


def test_all_expected_slash_commands_registered(tmp_path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    bot = MuteBot(db=db)
    bot.register_cogs_sync()
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cogs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mute_bot.bot'`

- [ ] **Step 3: Implement `ModerationCog`, `InteractionsCog`, `OnboardingCog`, `GiveawaysCog`, `MuteBot`, `mute_bot/main.py`, `Mute.py`, and `README.md`**

- `mute_bot/cogs/moderation.py`: `/ban`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/clearwarnings`, `on_message_edit`, `on_message_delete`.
- `mute_bot/cogs/interactions.py`: `on_message` (AutoMod text filter -> OCR attachment filter -> `handle_custom_mute`), `handle_custom_mute`, `automatic_unmute_log`.
- `mute_bot/cogs/onboarding.py`: `on_member_join`, `on_member_remove`, `on_raw_reaction_add`, `on_raw_reaction_remove`, `league_message_id()`, `notification_message_id()`, `handle_verification_reaction`, `handle_reaction_roles`, `update_member_count`, `/setup_verification_reactions`, `/setup_league_roles`, `/setup_notification_roles`, `/refresh_onboarding`, `/membercount`.
- `mute_bot/cogs/giveaways.py`: `resume_giveaways`, `finish_giveaway`, `giveaway_timer`, `/giveaway`, `/endgiveaway`, `/rerollgiveaway`.
- `mute_bot/bot.py`: `MuteBot(commands.Bot)` with `setup_hook()` loading all 4 cogs and syncing to `GUILD_OBJECT`, plus `register_cogs_sync()` helper for unit test inspection and `tree.on_error` handler.
- `mute_bot/main.py` & `Mute.py`: `main()` loads `.env`, configures logging and `pytesseract`, validates `BOT_TOKEN`, and runs `MuteBot`. `Mute.py` imports and calls `main()`.
- `README.md`: documents project structure, configuration, slash commands, testing, and deployment.

- [ ] **Step 4: Run the full test suite to verify all tests pass**

Run: `.venv/bin/pytest -v`
Expected: PASS (all test files green)

- [ ] **Step 5: Commit and push to `https://github.com/War-Robots-Guide/mute-bot.git`**

```bash
git add Mute.py README.md mute_bot/ tests/ docs/
git commit -m "feat: complete modular Cog refactoring of War Robots Guide Mute bot"
git push -u origin main
```
