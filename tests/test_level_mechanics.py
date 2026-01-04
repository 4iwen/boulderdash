import random
from unittest.mock import Mock

import pytest

from game.lvl.level import Level
from game.lvl.tiles import (
    AMOEBA,
    BUTTERFLY,
    DIAMOND,
    EMPTY,
    FIREFLY,
    PLAYER,
    ROCK,
    WALL,
)


def make_level_file(tmp_path, grid_lines, *, time_limit=999):
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


def test_level_loads_and_validates(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W X W",
            "W   W",
            "W  PW",
            "WWWWW",
        ],
    )

    level = Level(path)
    assert level.width == 5
    assert level.height == 5
    assert (level.player_x, level.player_y) != (-1, -1)
    assert (level.exit_x, level.exit_y) != (-1, -1)


def test_push_rock_horizontally(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWWW",
            "W    W",
            "W Xr W",
            "W   PW",
            "WWWWWW",
        ],
    )
    level = Level(path)

    px, py = level.player_x, level.player_y
    assert level.grid[py][px].type == PLAYER

    assert level.can_player_move_into(px, py, px + 1, py) is True
    assert level.grid[py][px + 1].type == EMPTY
    assert level.grid[py][px + 2].type == ROCK


def test_push_rock_blocked_does_not_push(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W XrW",
            "W   W",
            "W  PW",
            "WWWWW",
        ],
    )
    level = Level(path)

    px, py = level.player_x, level.player_y
    assert level.grid[py][px].type == PLAYER
    assert level.grid[py][px + 1].type == ROCK
    assert level.can_player_move_into(px, py, px + 1, py) is False
    assert level.grid[py][px + 1].type == ROCK


def test_falling_rock_kills_player_when_already_falling(tmp_path):
    killed = Mock()

    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W r W",
            "W X W",
            "W  PW",
            "WWWWW",
        ],
    )
    level = Level(path)
    level.on_player_killed = killed

    rock = level.grid[1][2]
    assert rock.type == ROCK
    rock.falling = True

    level._update_rocks_and_diamonds()

    assert killed.call_count == 1


@pytest.mark.parametrize("enemy_char", ["q", "B"])
def test_enemy_move_contact_kills_player(tmp_path, enemy_char):
    killed = Mock()

    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W X W",
            f"WW{enemy_char}WW",
            "WWWWW",
            "W  PW",
        ],
    )
    level = Level(path)
    level.on_player_killed = killed

    level._update_enemies()

    assert killed.call_count == 1


def test_rock_slides_left_when_supported(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W r W",
            "W r W",
            "W   W",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)

    level._update_rocks_and_diamonds()

    assert level.grid[1][1].type == ROCK
    assert level.grid[1][2].type == EMPTY


@pytest.mark.parametrize(
    "enemy_char, expected_center",
    [
        ("q", ROCK),
        ("B", DIAMOND),
    ],
)
def test_falling_rock_crushes_enemy(tmp_path, enemy_char, expected_center):
    path = make_level_file(
        tmp_path,
        [
            "WWWWWWW",
            "W  r  W",
            f"W  {enemy_char}  W",
            "W     W",
            "WXP   W",
            "WWWWWWW",
        ],
    )
    level = Level(path)
    falling = level.grid[1][3]
    falling.falling = True

    level._update_rocks_and_diamonds()

    assert level.grid[2][3].type == expected_center
    assert level.grid[2][3].type not in (FIREFLY, BUTTERFLY)


def test_falling_rock_crushing_butterfly_spawns_3x3_diamonds(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWWWW",
            "W  r  W",
            "W  B  W",
            "W     W",
            "WXP   W",
            "WWWWWWW",
        ],
    )
    level = Level(path)
    level.grid[1][3].falling = True

    level._update_rocks_and_diamonds()

    diamonds = 0
    for y in range(1, 4):
        for x in range(2, 5):
            if level.grid[y][x].type == DIAMOND:
                diamonds += 1
    assert diamonds == 9


@pytest.mark.parametrize("tile_char", ["r", "d"])
def test_magic_wall_does_not_transform_when_not_falling(tmp_path, tile_char):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            f"W {tile_char} W",
            "W m W",
            "W   W",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)
    obj = level.grid[1][2]
    obj.falling = False

    level._update_rocks_and_diamonds()

    assert level.grid[1][2].type in (ROCK, DIAMOND)
    assert level.grid[3][2].type == EMPTY


def test_magic_wall_does_not_transform_when_output_blocked(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "W r W",
            "W m W",
            "W w W",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)
    obj = level.grid[1][2]
    obj.falling = True
    assert level.grid[3][2].type == WALL

    level._update_rocks_and_diamonds()

    assert level.grid[1][2].type == ROCK
    assert level.grid[3][2].type == WALL
    assert level.grid[1][2].falling is False


@pytest.mark.parametrize(
    "enemy_char, expects_diamonds",
    [
        ("q", False),
        ("B", True),
    ],
)
def test_enemy_touching_amoeba_dies(tmp_path, enemy_char, expects_diamonds):
    path = make_level_file(
        tmp_path,
        [
            "WWWWWWW",
            "W     W",
            f"W  {enemy_char}a W",
            "W     W",
            "WXP   W",
            "WWWWWWW",
        ],
    )
    level = Level(path)

    level._update_enemies()

    if expects_diamonds:
        diamonds = 0
        for y in range(1, 4):
            for x in range(2, 5):
                if level.grid[y][x].type == DIAMOND:
                    diamonds += 1
        assert diamonds == 9
    else:
        assert level.grid[2][3].type == EMPTY


def test_amoeba_enclosed_turns_to_diamonds(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWWWW",
            "W  X  W",
            "W  P  W",
            "W WWW W",
            "W WaW W",
            "W WWW W",
            "WWWWWWW",
        ],
    )
    level = Level(path)

    level._update_amoeba()

    assert level.grid[4][3].type == DIAMOND


def test_amoeba_enclosed_turns_all_amoebas_to_diamonds(tmp_path):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "WwwwW",
            "WwawW",
            "WwawW",
            "WwwwW",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)

    before = sum(1 for row in level.grid for tile in row if tile.type == AMOEBA)
    assert before == 2

    level._update_amoeba()

    after_amoeba = sum(1 for row in level.grid for tile in row if tile.type == AMOEBA)
    after_diamond = sum(1 for row in level.grid for tile in row if tile.type == DIAMOND)
    assert after_amoeba == 0
    assert after_diamond >= before


def test_amoeba_grows_into_only_available_cell(tmp_path):
    random.seed(0)
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "WwwwW",
            "Wwa W",
            "WwwwW",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)
    level.AMOEBA_GROWTH_CHANCE = 1.0

    level._update_amoeba()

    assert level.grid[2][3].type == AMOEBA


def test_amoeba_max_size_turns_to_boulders(tmp_path):
    random.seed(0)
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            "WwwwW",
            "Wwa W",
            "WwwwW",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)
    level.AMOEBA_GROWTH_CHANCE = 1.0
    level.AMOEBA_MAX_SIZE = 2

    level._update_amoeba()

    amoebas = sum(1 for row in level.grid for tile in row if tile.type == AMOEBA)
    rocks = sum(1 for row in level.grid for tile in row if tile.type == ROCK)
    assert amoebas == 0
    assert rocks == 2


@pytest.mark.parametrize(
    "tile_char, expected_out",
    [
        ("r", DIAMOND),
        ("d", ROCK),
    ],
)
def test_magic_wall_transforms_falling_objects(tmp_path, tile_char, expected_out):
    path = make_level_file(
        tmp_path,
        [
            "WWWWW",
            f"W {tile_char} W",
            "W m W",
            "W   W",
            "WXP W",
            "WWWWW",
        ],
    )
    level = Level(path)

    obj = level.grid[1][2]
    obj.falling = True

    level._update_rocks_and_diamonds()

    assert level.grid[3][2].type == expected_out
