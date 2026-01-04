"""YAML configuration loader for the game."""

from pathlib import Path

import yaml


class Config:
    """Config loaded from a YAML file"""

    def __init__(self, path):
        self.path = Path(path)
        self.data = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as file:
            try:
                self.data = yaml.safe_load(file) or {}
            except yaml.YAMLError as error:
                raise ValueError(f"Error parsing YAML: {error}") from error

        return self

    def get(self, key, default=None):
        return self.data.get(key, default)
