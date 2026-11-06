# War Robots Guide — `mute-bot`

Moderation, onboarding, reaction-role, giveaway, and OCR AutoMod Discord bot for the **War Robots Guide** community server.

## Architecture

```text
mute-bot/
├── Mute.py                          # Backwards-compatible entrypoint (for Wispbyte/hosts)
├── pyproject.toml                   # Package metadata, dependencies, and pytest configuration
├── requirements.txt                 # Production dependencies
├── .env.example                     # Environment variable template
├── mute_bot/
│   ├── main.py                      # Application bootstrap, logging, token & Tesseract setup
│   ├── config.py                    # Guild, role, channel, message, and threshold constants
│   ├── database.py                  # SQLite persistence (warnings, settings, onboarding, giveaways)
│   ├── bot.py                       # MuteBot(commands.Bot), Cog loader, global error handler
│   ├── data/
│   │   └── responses.py             # @Mute lore responses, 8-ball answers, and AutoMod terms
│   ├── services/
│   │   ├── automod.py               # Homoglyph/leetspeak text filter and Pillow + Tesseract OCR
│   │   ├── discord_helpers.py       # Ephemeral replies, reliable replies, embed & role helpers
│   │   ├── formatting.py            # Duration parser, cooldown formatter, ordinal & emoji helpers
│   │   ├── logging_service.py       # Moderation, troll, and AutoMod embed loggers
│   │   ├── mute_chat.py             # @Mute mention/phrase/question parsers and CooldownTracker
│   │   └── permissions.py           # Staff/admin role checks and moderation hierarchy validation
│   └── cogs/
│       ├── giveaways.py             # /giveaway, /endgiveaway, /rerollgiveaway, persistent timers
│       ├── interactions.py          # on_message pipeline: AutoMod -> OCR -> @Mute interactions
│       ├── moderation.py            # /ban, /mute, /unmute, /warn, /warnings, /clearwarnings, audit logs
│       └── onboarding.py            # Join/leave, verification reactions, reaction roles, member count
└── tests/                           # Automated unit and Cog integration test suite
```

## Setup & Running

1. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Copy `.env.example` to `.env` and set your Discord bot token:
   ```bash
   cp .env.example .env
   ```

   Optional: install `tesseract-ocr` on the host machine to enable image attachment OCR filtering.

3. **Start the bot:**
   ```bash
   python Mute.py
   # or
   python -m mute_bot.main
   ```

## Running Tests

```bash
pytest -v
```
