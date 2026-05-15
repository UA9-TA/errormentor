import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".errormentor"
        self.config_file = self.config_dir / "config.toml"
        self._config = {}
        self.load()

    def load(self):
        if self.config_file.exists():
            with open(self.config_file, "rb") as f:
                self._config = tomllib.load(f)

        # Override with env vars
        if "ANTHROPIC_API_KEY" in os.environ:
            self._config["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]

    def get(self, key, default=None):
        return self._config.get(key, default)

config = Config()
