# War Robots Guide `mute-bot` Refactoring Design Spec

## Intent and Why

`Mute.py` is currently a 3,616-line single-file script powering the War Robots Guide Discord server (`GUILD_ID = 1197548660188254228`). Over time, it accumulated five distinct responsibilities (onboarding & reaction roles, OCR/text AutoMod, `@Mute` chat interactions, staff moderation & audit logging, and giveaways) alongside roughly 800 lines of dead code from a retired per-member channel-permission-lock system.

The goal of this refactoring is to transform the monolith into a modular, testable, idiomatic `discord.py` codebase in the `https://github.com/War-Robots-Guide/mute-bot.git` repository while preserving 100% of active production behavior, database compatibility (`mute_bot.sqlite3`), and hosting compatibility (`Mute.py` entrypoint).

## Goals, Non-Goals, and Anti-Goals

### Goals
- **Modular architecture:** Decompose the monolith into focused `discord.py` Cogs, pure domain services, a typed configuration module, and a self-contained SQLite repository (`Database`).
- **Behavioral parity:** Preserve all active commands, event listeners, permissions, cooldowns, role hierarchies, embed formats, and response strings.
- **Dead code removal:** Remove unreachable remnants from the retired channel-overwrite onboarding system (`set_channel_access`, `clear_member_overwrite`, `clear_onboarding_permission_fields`, `synchronize_all_members_from_reactions`, `restore_all_member_channel_overwrites_on_startup`, `onboarding_reconciliation_loop`, `grandfather_existing_members`, `protected_onboarding_channel_ids`, `allowed_emoji_only`, `is_plain_mute`).
- **Panel ID consistency fix:** Allow `handle_reaction_roles` to honor panel message IDs saved to SQLite by `/setup_league_roles` and `/setup_notification_roles`, falling back to the configured default message IDs (`LEAGUE_MESSAGE`, `NOTIFICATION_MESSAGE`).
- **Automated test suite:** Provide unit tests covering database operations, duration parsing, moderation hierarchy checks, homoglyph/leetspeak text filtering, `@Mute` phrase/question parsing, cooldown tracking, and cog command/event logic without requiring a live Discord token.
- **Git & packaging standards:** Initialize the repository with `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, and push to `https://github.com/War-Robots-Guide/mute-bot.git`.

### Non-Goals
- Migrating away from SQLite (`mute_bot.sqlite3`) or breaking existing database schemas.
- Changing Discord role IDs, channel IDs, cooldown values, or lore/response copy.
- Adding external infrastructure requirements (e.g., Redis, PostgreSQL, Docker-only runtime).

### Anti-Goals
- Breaking import-time execution when `BOT_TOKEN` is unset (tests and tooling must be able to import all modules without `.env` present).
- Breaking existing Wispbyte/host startup configurations that invoke `python Mute.py`.

## Constraints

- **Runtime:** Python `>=3.11` (compatible with 3.11–3.14), `discord.py >=2.3`, `Pillow`, `pytesseract`, `python-dotenv`.
- **Database compatibility:** SQLite file path defaults to `mute_bot.sqlite3` in the project root; existing tables (`warnings`, `settings`, `onboarding`, `giveaways`) and column names must remain identical.
- **Entrypoint compatibility:** Root `Mute.py` must remain a working entrypoint delegating to `mute_bot.main:main`.
- **Event ordering:** In message handling, AutoMod text and OCR attachment checks must execute before `@Mute` custom interactions; if a message contains a banned term in text or image OCR, it is deleted and must never trigger an `@Mute` reply.

## Approaches Considered

### Approach 1: `discord.py` Cogs + Domain Services Package (Selected)
Organize the codebase into a `mute_bot/` package with:
- `mute_bot/config.py` and `mute_bot/data/responses.py` for constants and server copy.
- `mute_bot/database.py` for SQLite persistence.
- `mute_bot/services/` for pure/testable business logic (text/OCR filtering, `@Mute` parsing and cooldown state, duration/emoji formatting, permission checks, logging embeds).
- `mute_bot/cogs/` for Discord event listeners and slash commands (`ModerationCog`, `OnboardingCog`, `InteractionsCog`, `GiveawaysCog`).
- Root `Mute.py` as a thin compatibility wrapper calling `mute_bot.main:main()`.

**Trade-offs:** Slightly more files than a flat split, but separates pure logic (testable in milliseconds without Discord mocks) from Discord I/O (Cogs).

### Approach 2: Flat Module Split Only
Split `Mute.py` into 4–5 sibling `.py` files in the root directory sharing a global `bot` instance and `@bot.event` / `@bot.tree.command` decorators.

**Trade-offs:** Minimal file movement, but retains circular import hazards, import-time side effects, global mutable state (`MUTE_SHARED_COOLDOWNS`, `REACTION_MEMBER_LOCKS`), and poor testability because Discord allows only one `@bot.event` handler per event name across the global bot instance.

### Approach 3: Full Hexagonal / Async ORM Rewrite (`SQLAlchemy` + `aiosqlite`)
Replace raw SQLite with async SQLAlchemy models, dependency injection containers, and abstract repository interfaces.

**Trade-offs:** Over-engineered for a single-guild bot with four small SQLite tables; adds unnecessary dependencies and migration complexity.

## Target Package Architecture

```text
mute-bot/
├── Mute.py                          # Backwards-compatible entrypoint for Wispbyte
├── pyproject.toml                   # Project metadata, dependencies, pytest/ruff config
├── requirements.txt                 # Production dependencies for hosting platforms
├── .env.example                     # Example environment variables (BOT_TOKEN, TESSERACT_COMMAND)
├── .gitignore                       # Ignores .env, *.sqlite3*, __pycache__, .venv, etc.
├── README.md                        # Architecture, setup, slash commands, and deployment guide
├── mute_bot/
│   ├── __init__.py
│   ├── main.py                      # CLI/entrypoint, logging setup, token validation, bot.run()
│   ├── config.py                    # Guild/role/channel/message IDs, thresholds, OCR settings
│   ├── data/
│   │   ├── __init__.py
│   │   └── responses.py             # Enlighten lore, 8-ball responses, ping replies, banned terms
│   ├── database.py                  # Database class managing warnings, settings, onboarding, giveaways
│   ├── bot.py                       # MuteBot(commands.Bot), cog loader, global app_command error handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── formatting.py            # parse_duration, format_cooldown_time, identity, ordinal, emoji helpers
│   │   ├── permissions.py           # is_staff, is_admin, reply_mute_level, can_moderate, check decorators
│   │   ├── discord_helpers.py       # reliable_message_reply, reply_ephemeral, delete_message, send_embed
│   │   ├── logging_service.py       # modlog, troll_log, automod_log
│   │   ├── automod.py               # normalize_filter_text, find_banned_term, preprocess_ocr, run_ocr
│   │   └── mute_chat.py             # @Mute phrase/question parsers, CooldownTracker
│   └── cogs/
│       ├── __init__.py
│       ├── moderation.py            # /ban, /mute, /unmute, /warn, /warnings, /clearwarnings, edit/delete logs
│       ├── interactions.py          # on_message pipeline: AutoMod filter -> OCR -> @Mute interactions
│       ├── onboarding.py            # Join/leave, verification reactions, reaction roles, member count
│       └── giveaways.py             # /giveaway, /endgiveaway, /rerollgiveaway, persistent timers
└── tests/
    ├── __init__.py
    ├── test_database.py
    ├── test_formatting.py
    ├── test_permissions.py
    ├── test_automod.py
    ├── test_mute_chat.py
    └── test_cogs.py
```
