from datetime import datetime, timezone
import importlib
import sqlite3
import pytest
import mute_bot.config as config_module
from mute_bot.config import GUILD_ID, LEAGUE_ROLES, PLATFORM_ROLES, NOTIFICATION_ROLES
from mute_bot.data.responses import BANNED_TERMS, CUSTOM_MUTE_PHRASES, ENLIGHTEN_RESPONSES, QUESTION_RESPONSES
from mute_bot.database import Database


def test_config_loads_dotenv_before_tesseract_command(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(
        "dotenv.load_dotenv",
        lambda *args, **kwargs: called.append(True),
        raising=False,
    )
    importlib.reload(config_module)
    assert called, "mute_bot.config must call load_dotenv() before reading TESSERACT_COMMAND"



def test_config_and_responses_preserved() -> None:
    assert GUILD_ID == 1197548660188254228
    assert len(LEAGUE_ROLES) == 8
    assert len(PLATFORM_ROLES) == 4
    assert len(NOTIFICATION_ROLES) == 2
    assert "enlighten me" not in CUSTOM_MUTE_PHRASES
    assert "get him" in CUSTOM_MUTE_PHRASES
    assert len(ENLIGHTEN_RESPONSES) == 50
    assert len(QUESTION_RESPONSES) == 69
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
