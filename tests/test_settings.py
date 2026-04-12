import json
from pathlib import Path

from mista_wispa.settings import Settings


def test_default_settings():
    s = Settings()
    assert s.llm_cleanup_enabled is False
    assert s.llm_server_url == "http://127.0.0.1:1234/v1"


def test_load_from_file(tmp_path):
    config = {"llm_cleanup_enabled": True, "llm_server_url": "http://localhost:9999/v1"}
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(config))

    s = Settings(config_path=config_file)
    assert s.llm_cleanup_enabled is True
    assert s.llm_server_url == "http://localhost:9999/v1"


def test_save_creates_file(tmp_path):
    config_file = tmp_path / "subdir" / "settings.json"
    s = Settings(config_path=config_file)
    s.llm_cleanup_enabled = True
    s.save()

    loaded = json.loads(config_file.read_text())
    assert loaded["llm_cleanup_enabled"] is True


def test_missing_file_uses_defaults(tmp_path):
    config_file = tmp_path / "nonexistent" / "settings.json"
    s = Settings(config_path=config_file)
    assert s.llm_cleanup_enabled is False
