"""Level loading and simulation"""

import random
import tomllib
from pathlib import Path

from game.lvl.tiles import (
    AMOEBA,
    BUTTERFLY,
    DIAMOND,
    DIRT,
    EMPTY,
    EXIT,
    FIREFLY,
    MAGIC_WALL,
    PLAYER,
    ROCK,
    TILE_SPRITES,
    TITANIUM_WALL,
    WALL,
    Tile,
)


class Level:
    TILEMAP = {
        " ": EMPTY,
        ".": DIRT,
        "r": ROCK,
        "d": DIAMOND,
        "w": WALL,
        "X": PLAYER,
        "P": EXIT,
        "W": TITANIUM_WALL,
        "m": MAGIC_WALL,
        "a": AMOEBA,
        "q": FIREFLY,
        "B": BUTTERFLY
    }

    LEVEL_UPDATE_DELAY = 0.2
    AMOEBA_GROWTH_CHANCE = 0.05
    AMOEBA_MAX_SIZE = 200

    def __init__(self, path):
        self.path = Path(path)
        self.data = {}
        self.name = ""
        self.width = 0
        self.height = 0
        self.grid: list[list[Tile]] = []
        self.colors = {}
        self.time_limit = 0
        self.diamonds_required = 0
        self.diamond_value = 0
        self.bonus_diamond_value = 0
        self.player_x = -1
        self.player_y = -1

        self.exit_x = -1
        self.exit_y = -1

        self.timer = 0.0

        self.renderer = None

        self.on_player_killed: callable | None = None

        self._load()

    def _load(self):
        with self.path.open("rb") as file:
            self.data = tomllib.load(file)

        meta = self.data.get("meta", {})
        self.name = meta.get("name", "Unnamed Level")
        self.time_limit = meta.get("time_limit", 300)
        self.diamonds_required = meta.get("diamonds_required", 0)
        self.diamond_value = meta.get("diamond_value", 10)
        self.bonus_diamond_value = meta.get("bonus_diamond_value", 10)
        self.colors = self.data.get("colors", {})

        level_data = self.data.get("level", {}).get("data", "")
        self._parse_level_data(level_data)
        self._find_player()
        self._find_exit()
        self._validate()
        return self

    def _parse_level_data(self, data):
        lines = [line.strip() for line in data.strip().split("\n") if line.strip()]
        self.height = len(lines)
        self.width = len(lines[0]) if lines else 0
        self.grid = [[Tile(self.TILEMAP.get(char, EMPTY)) for char in line] for line in lines]

    def _find_player(self):
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.type == PLAYER:
                    self.player_x = x
                    self.player_y = y
                    return

    def _find_exit(self):
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.type == EXIT:
                    self.exit_x = x
                    self.exit_y = y
                    return

    def _validate(self):
        """
        Each level has to have a player, exit, be rectangular, and have valid tile types.
        """
        if self.player_x == -1 or self.player_y == -1:
            raise ValueError("Level must have a player.")

        if self.exit_x == -1 or self.exit_y == -1:
            raise ValueError("Level must have an exit.")

        for row in self.grid:
            if len(row) != self.width:
                raise ValueError("Level rows must be of equal width.")

        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.type not in TILE_SPRITES:
                    raise ValueError(f"Invalid tile type at ({x}, {y}).")

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.LEVEL_UPDATE_DELAY:
            self.timer = 0.0
            self._update_rocks_and_diamonds()
            self._update_amoeba()
            self._update_enemies()

    def _update_amoeba(self):
        old_types = [[tile.type for tile in row] for row in self.grid]

        amoebas: list[tuple[int, int]] = []
        possible_growth: list[tuple[int, int]] = []

        for y in range(self.height):
            for x in range(self.width):
                if old_types[y][x] != AMOEBA:
                    continue
                amoebas.append((x, y))
                for nx, ny in self._neighbors4(x, y):
                    if old_types[ny][nx] in (EMPTY, DIRT):
                        possible_growth.append((nx, ny))

        if not amoebas:
            return

        if not possible_growth:
            for x, y in amoebas:
                tile = self.grid[y][x]
                if tile.sprite_name == "explosion":
                    continue
                tile.set_type(DIAMOND)
                if self.renderer:
                    self.renderer.update_tile_sprite(tile)
            return

        occupied_new: set[tuple[int, int]] = set()

        for ax, ay in amoebas:
            if random.random() > self.AMOEBA_GROWTH_CHANCE:
                continue

            candidates = []
            for nx, ny in self._neighbors4(ax, ay):
                if old_types[ny][nx] in (EMPTY, DIRT) and (nx, ny) not in occupied_new:
                    candidates.append((nx, ny))

            if not candidates:
                continue

            gx, gy = random.choice(candidates)
            occupied_new.add((gx, gy))

        for gx, gy in occupied_new:
            tile = self.grid[gy][gx]
            if tile.sprite_name == "explosion":
                continue
            tile.set_type(AMOEBA)
            if self.renderer:
                self.renderer.update_tile_sprite(tile)

        if self.AMOEBA_MAX_SIZE > 0:
            new_size = len(amoebas) + len(occupied_new)
            if new_size >= self.AMOEBA_MAX_SIZE:
                for y in range(self.height):
                    for x in range(self.width):
                        tile = self.grid[y][x]
                        if tile.type != AMOEBA:
                            continue
                        if tile.sprite_name == "explosion":
                            continue
                        tile.set_type(ROCK)
                        if self.renderer:
                            self.renderer.update_tile_sprite(tile)

    def can_player_move_into(self, px: int, py: int, nx: int, ny: int) -> bool:
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return False

        target = self.grid[ny][nx]
        dx = nx - px
        dy = ny - py

        if target.type == ROCK and dy == 0 and dx != 0:
            push_x = nx + dx
            push_y = ny
            if 0 <= push_x < self.width:
                push_target = self.grid[push_y][push_x]
                if push_target.type == EMPTY:
                    push_target.set_type(ROCK)
                    target.set_type(EMPTY)
                    if self.renderer:
                        self.renderer.update_tile_sprite(push_target)
                        self.renderer.update_tile_sprite(target)
                    return True
            return False

        if target.is_solid() and target.type not in (DIRT, DIAMOND, EXIT):
            return False

        return True

    def _update_rocks_and_diamonds(self):
        old_grid = [[tile.type for tile in row] for row in self.grid]
        old_falling = [[tile.falling for tile in row] for row in self.grid]

        new_grid = [row[:] for row in old_grid]
        new_falling = [[False for _ in row] for row in self.grid]

        for y in range(self.height - 2, -1, -1):
            for x in range(self.width):
                tile_type = old_grid[y][x]

                if tile_type not in (ROCK, DIAMOND):
                    continue

                was_falling = old_falling[y][x]
                below = old_grid[y + 1][x]

                if below == EMPTY:
                    new_grid[y][x] = EMPTY
                    new_grid[y + 1][x] = tile_type
                    new_falling[y + 1][x] = True
                    continue

                if below == MAGIC_WALL and was_falling:
                    out_y = y + 2
                    if out_y < self.height and old_grid[out_y][x] == EMPTY:
                        new_grid[y][x] = EMPTY
                        if tile_type == ROCK:
                            out_type = DIAMOND
                        else:
                            out_type = ROCK
                        new_grid[out_y][x] = out_type
                        new_falling[out_y][x] = True
                    else:
                        new_falling[y][x] = False
                    continue

                if below == PLAYER and was_falling:
                    new_grid[y][x] = EMPTY
                    new_grid[y + 1][x] = tile_type
                    new_falling[y + 1][x] = False
                    if self.on_player_killed:
                        self.on_player_killed()
                    continue

                if below in (FIREFLY, BUTTERFLY) and was_falling:
                    new_grid[y][x] = EMPTY
                    if below == BUTTERFLY:
                        self._spawn_butterfly_diamonds_into_grid(new_grid, y + 1, x)
                        self._clear_falling_in_area(new_falling, y + 1, x)
                    else:
                        new_grid[y + 1][x] = tile_type
                        new_falling[y + 1][x] = False
                    continue

                if below in (ROCK, DIAMOND, WALL):
                    slid = False

                    # try left
                    if x > 0:
                        left = old_grid[y][x - 1]
                        below_left = old_grid[y + 1][x - 1]
                        if left == EMPTY and below_left == EMPTY:
                            new_grid[y][x] = EMPTY
                            new_grid[y][x - 1] = tile_type
                            new_falling[y][x - 1] = True
                            slid = True

                    # try right
                    if not slid and x < self.width - 1:
                        right = old_grid[y][x + 1]
                        below_right = old_grid[y + 1][x + 1]
                        if right == EMPTY and below_right == EMPTY:
                            new_grid[y][x] = EMPTY
                            new_grid[y][x + 1] = tile_type
                            new_falling[y][x + 1] = True
                            slid = True

                    if not slid:
                        new_falling[y][x] = False
                else:
                    new_falling[y][x] = False

        for y in range(self.height):
            for x in range(self.width):
                tile = self.grid[y][x]
                new_type = new_grid[y][x]

                if tile.sprite_name == "explosion":
                    tile.falling = new_falling[y][x]
                    continue

                if tile.type != new_type:
                    tile.set_type(new_type)
                    if self.renderer:
                        self.renderer.update_tile_sprite(tile)

                tile.falling = new_falling[y][x]

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _neighbors4(self, x: int, y: int):
        if y > 0:
            yield x, y - 1
        if x < self.width - 1:
            yield x + 1, y
        if y < self.height - 1:
            yield x, y + 1
        if x > 0:
            yield x - 1, y

    def _spawn_butterfly_diamonds_into_grid(self, grid_types: list[list[int]], cy: int, cx: int):
        preserve = {TITANIUM_WALL, EXIT, PLAYER}
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x = cx + dx
                y = cy + dy
                if not self._in_bounds(x, y):
                    continue
                if grid_types[y][x] in preserve:
                    continue
                grid_types[y][x] = DIAMOND

    def _clear_falling_in_area(self, falling: list[list[bool]], cy: int, cx: int):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x = cx + dx
                y = cy + dy
                if self._in_bounds(x, y):
                    falling[y][x] = False

    def _update_enemies(self):
        old_types = [[tile.type for tile in row] for row in self.grid]
        old_dir = [[tile.enemy_dir for tile in row] for row in self.grid]
        old_wait = [[tile.enemy_wait for tile in row] for row in self.grid]
        old_paused = [[tile.enemy_paused for tile in row] for row in self.grid]

        new_types = [row[:] for row in old_types]
        new_dir = [row[:] for row in old_dir]
        new_wait = [row[:] for row in old_wait]
        new_paused = [row[:] for row in old_paused]

        moved_into = [[False for _ in range(self.width)] for _ in range(self.height)]

        def vec_for_dir(d: int) -> tuple[int, int]:
            return (
                (0, -1),
                (1, 0),
                (0, 1),
                (-1, 0),
            )[d % 4]

        def is_empty(x: int, y: int) -> bool:
            return self._in_bounds(x, y) and old_types[y][x] == EMPTY and not moved_into[y][x]

        def is_player(x: int, y: int) -> bool:
            return self._in_bounds(x, y) and old_types[y][x] == PLAYER

        def touches_amoeba(x: int, y: int) -> bool:
            for nx, ny in self._neighbors4(x, y):
                if old_types[ny][nx] == AMOEBA:
                    return True
            return False

        def kill_enemy_at(x: int, y: int, enemy_type: int):
            if enemy_type == BUTTERFLY:
                self._spawn_butterfly_diamonds_into_grid(new_types, y, x)
            else:
                new_types[y][x] = EMPTY
            new_dir[y][x] = 0
            new_wait[y][x] = 0
            new_paused[y][x] = False

        for y in range(self.height):
            for x in range(self.width):
                t = old_types[y][x]
                if t not in (FIREFLY, BUTTERFLY):
                    continue

                if touches_amoeba(x, y):
                    kill_enemy_at(x, y, t)
                    continue

                wait = old_wait[y][x]
                if wait > 0:
                    new_wait[y][x] = wait - 1
                    continue

                d = old_dir[y][x] % 4
                left_d = (d + 3) % 4
                right_d = (d + 1) % 4
                back_d = (d + 2) % 4

                preferred_d = left_d if t == FIREFLY else right_d
                secondary_d = right_d if t == FIREFLY else left_d

                pdx, pdy = vec_for_dir(preferred_d)
                fdx, fdy = vec_for_dir(d)
                sdx, sdy = vec_for_dir(secondary_d)
                bdx, bdy = vec_for_dir(back_d)

                preferred_empty = is_empty(x + pdx, y + pdy)
                forward_empty = is_empty(x + fdx, y + fdy)

                forward_is_player = is_player(x + fdx, y + fdy)
                preferred_is_player = is_player(x + pdx, y + pdy)

                if (not preferred_empty) and (not forward_empty) and (not old_paused[y][x]):
                    if forward_is_player or preferred_is_player:
                        if self.on_player_killed:
                            self.on_player_killed()
                        continue
                    new_wait[y][x] = 1
                    new_paused[y][x] = True
                    continue

                candidates = [
                    (preferred_d, pdx, pdy),
                    (d, fdx, fdy),
                    (secondary_d, sdx, sdy),
                    (back_d, bdx, bdy),
                ]

                moved = False
                for nd, ddx, ddy in candidates:
                    nx = x + ddx
                    ny = y + ddy

                    # Enemy touching player kills the player.
                    if is_player(nx, ny):
                        if self.on_player_killed:
                            self.on_player_killed()
                        moved = False
                        break

                    if not is_empty(nx, ny):
                        continue

                    new_types[y][x] = EMPTY
                    new_types[ny][nx] = t
                    new_dir[ny][nx] = nd
                    new_wait[ny][nx] = 0
                    new_paused[ny][nx] = False
                    moved_into[ny][nx] = True

                    new_dir[y][x] = 0
                    new_wait[y][x] = 0
                    new_paused[y][x] = False
                    moved = True
                    break

                if not moved:
                    new_paused[y][x] = old_paused[y][x]

        for y in range(self.height):
            for x in range(self.width):
                tile = self.grid[y][x]
                nt = new_types[y][x]
                if tile.sprite_name == "explosion":
                    continue

                if tile.type != nt:
                    tile.set_type(nt)
                    if self.renderer:
                        self.renderer.update_tile_sprite(tile)

                tile.enemy_dir = new_dir[y][x]
                tile.enemy_wait = new_wait[y][x]
                tile.enemy_paused = new_paused[y][x]

        current_types = [[tile.type for tile in row] for row in self.grid]
        for y in range(self.height):
            for x in range(self.width):
                t = current_types[y][x]
                if t not in (FIREFLY, BUTTERFLY):
                    continue
                adjacent = False
                for nx, ny in self._neighbors4(x, y):
                    if current_types[ny][nx] == AMOEBA:
                        adjacent = True
                        break
                if not adjacent:
                    continue

                if t == BUTTERFLY:
                    preserve = {TITANIUM_WALL, EXIT, PLAYER}
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ax = x + dx
                            ay = y + dy
                            if not self._in_bounds(ax, ay):
                                continue
                            atile = self.grid[ay][ax]
                            if atile.type in preserve:
                                continue
                            atile.set_type(DIAMOND)
                            if self.renderer:
                                self.renderer.update_tile_sprite(atile)
                else:
                    tile = self.grid[y][x]
                    tile.set_type(EMPTY)
                    if self.renderer:
                        self.renderer.update_tile_sprite(tile)
