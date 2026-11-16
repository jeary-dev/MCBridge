import os

from mcbridge_bot.config import Settings, load_env_file

KEYS = ["DISCORD_TOKEN", "DEV_GUILD_ID", "PORT", "CHAT_BRIDGE", "PUBLIC_WS_URL"]


def test_env_file_and_defaults(tmp_path, monkeypatch):
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text('# comment\nDISCORD_TOKEN="abc"\nDEV_GUILD_ID=123\nCHAT_BRIDGE=false\nPUBLIC_WS_URL=\n')
    load_env_file(env)
    s = Settings.from_env()
    assert s.discord_token == "abc" and s.dev_guild_id == 123
    assert s.chat_bridge is False and s.public_ws_url is None and s.port == 8765
    for k in KEYS:
        os.environ.pop(k, None)


def test_real_environment_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    env = tmp_path / ".env"
    env.write_text("PORT=1234\n")
    load_env_file(env)
    assert Settings.from_env().port == 9000


def test_missing_file_is_fine(tmp_path):
    load_env_file(tmp_path / "nope.env")
