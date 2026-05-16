import os
import sys

# Support Python < 3.11 for tomllib
if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

class Config:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.errormentor")
        self.config_file = os.path.join(self.config_dir, "config.toml")
        self.data = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return {}

    def get_api_key(self) -> str:
        # Check env var first
        if key := os.getenv("ANTHROPIC_API_KEY"):
            return key

        # Check config file
        return self.data.get("ai", {}).get("anthropic_api_key", "")
