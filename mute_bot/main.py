from __future__ import annotations

import logging
import os

import pytesseract
from dotenv import load_dotenv

from mute_bot.bot import MuteBot
from mute_bot.config import TESSERACT_COMMAND


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger("Mute")


def main() -> None:
    load_dotenv()
    log = setup_logging()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN was not found in .env")

    token = bot_token.strip()
    if not token or token == "PASTE_YOUR_DISCORD_BOT_TOKEN_HERE":
        raise RuntimeError(
            "Set BOT_TOKEN in the Wispbyte .env/environment variables."
        )

    if TESSERACT_COMMAND:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_COMMAND
    else:
        log.warning(
            "Tesseract is not installed; OCR image scanning is disabled."
        )

    bot = MuteBot()
    bot.run(token)


if __name__ == "__main__":
    main()
