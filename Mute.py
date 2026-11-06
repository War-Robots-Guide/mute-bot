"""Backwards-compatible entrypoint for Wispbyte and legacy startup scripts."""

from __future__ import annotations

from mute_bot.main import main

if __name__ == "__main__":
    main()
