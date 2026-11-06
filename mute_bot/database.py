from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mute_bot.config import DB_PATH, GUILD_ID

ALLOWED_ONBOARDING_FIELDS = {
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


class Database:
    def __init__(self, path: Path = DB_PATH, guild_id: int = GUILD_ID) -> None:
        self.path = path
        self.guild_id = guild_id
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
                (self.guild_id, user_id),
            )
            connection.commit()

    def has_onboarding(self, user_id: int) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM onboarding WHERE guild_id = ? AND user_id = ?",
                (self.guild_id, user_id),
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
                (self.guild_id, user_id),
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
                (self.guild_id, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("Onboarding data could not be created.")
            return row

    def set_onboarding(self, user_id: int, field: str, value: object) -> None:
        if field not in ALLOWED_ONBOARDING_FIELDS:
            raise ValueError(field)

        self.ensure_user(user_id)
        with self.connect() as connection:
            connection.execute(
                f"""
                UPDATE onboarding
                SET {field} = ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (value, self.guild_id, user_id),
            )
            connection.commit()

    def delete_onboarding(self, user_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM onboarding WHERE guild_id = ? AND user_id = ?",
                (self.guild_id, user_id),
            )
            connection.commit()

    def setting(self, key: str) -> Optional[str]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT value FROM settings
                WHERE guild_id = ? AND key = ?
                """,
                (self.guild_id, key),
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
                (self.guild_id, key, value),
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
                    self.guild_id,
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
                    (self.guild_id, user_id),
                ).fetchall()
            )

    def clear_warnings(self, user_id: int) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
                (self.guild_id, user_id),
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
                    self.guild_id,
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
