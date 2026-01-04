from unittest.mock import Mock
import pytest
from game.game import Game


class DummyConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class DummyRenderer:
    def __init__(self):
        self.width = 640
        self.height = 400
        self.restart_darkness = 0.0

    def set_level(self, level):
        pass

    def update_tile_sprite(self, tile):
        pass

    def start_flash(self, duration=None):
        pass

    def push_handlers(self, *args, **kwargs):
        pass


def make_level_file(tmp_path, grid_lines, *, time_limit=1):
    data = "\n".join(grid_lines)
    toml = f"""[meta]
name = \"Test\"
time_limit = {time_limit}
diamonds_required = 0
diamond_value = 10
bonus_diamond_value = 10

[colors]
background1 = \"gray1\"
background2 = \"brown\"
foreground = \"white\"

[level]
data = \"\"\"\n{data}\n\"\"\"\n"""
    path = tmp_path / "level.toml"
    path.write_text(toml)
    return path


def make_headless_game(monkeypatch, level_path):
    monkeypatch.setattr(Game, "LEVELS", [str(level_path)])
    return Game(DummyConfig(render_scale=2), headless=True, renderer=DummyRenderer())


@pytest.mark.parametrize("enemy_char", ["q", "B"])
def test_player_moving_into_enemy_kills_player(tmp_path, monkeypatch, enemy_char):
    level_path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            f"W X{enemy_char}W",
            "W   W",
            "W  PW",
            "WWWWW",
        ],
        time_limit=999,
    )

    game = make_headless_game(monkeypatch, level_path)
    assert game.is_dying is False

    game._move_player(1, 0)
    assert game.is_dying is True


def test_timer_reaching_zero_kills_player(tmp_path, monkeypatch):
    level_path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W X W",
            "W   W",
            "W  PW",
            "WWWWW",
        ],
        time_limit=1,
    )

    game = make_headless_game(monkeypatch, level_path)
    game.time_remaining = 0.05

    original_kill = game._kill_player
    spy = Mock(wraps=original_kill)
    monkeypatch.setattr(game, "_kill_player", spy)

    game.update(0.2)

    assert game.is_dying is True
    assert game.time_remaining == 0
    assert spy.call_count == 1
