import json
from pathlib import Path

_DEFAULT_PATH = Path.home() / ".config" / "mista-wispa" / "settings.json"

_DEFAULTS = {
    "llm_cleanup_enabled": False,
    "llm_server_url": "http://127.0.0.1:1234/v1",
}


class Settings:
    def __init__(self, config_path: Path | None = None):
        self._path = config_path or _DEFAULT_PATH
        data = _DEFAULTS.copy()
        if self._path.exists():
            with open(self._path) as f:
                data.update(json.load(f))
        self.llm_cleanup_enabled: bool = data["llm_cleanup_enabled"]
        self.llm_server_url: str = data["llm_server_url"]

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(
                {
                    "llm_cleanup_enabled": self.llm_cleanup_enabled,
                    "llm_server_url": self.llm_server_url,
                },
                f,
                indent=2,
            )
