import random

import pyglet
from pyglet.window import key
from pyglet.math import Vec3
from game.cfg.config import Config
from game.lvl.level import Level
from game.lvl.tiles import BUTTERFLY, DIAMOND, EMPTY, EXIT, FIREFLY, PLAYER


class Game:
    LEVELS = [
        "assets/levels/cave1.toml",
        "assets/levels/cave2.toml",
        "assets/levels/cave3.toml",
        "assets/levels/cave4.toml",
        "assets/levels/intermission1.toml",
        "assets/levels/cave5.toml",
        "assets/levels/cave6.toml",
        "assets/levels/cave7.toml",
        "assets/levels/cave8.toml",
        "assets/levels/intermission2.toml",
        "assets/levels/cave9.toml",
        "assets/levels/cave10.toml",
        "assets/levels/cave11.toml",
        "assets/levels/cave12.toml",
        "assets/levels/intermission3.toml",
        "assets/levels/cave13.toml",
        "assets/levels/cave14.toml",
        "assets/levels/cave15.toml",
        "assets/levels/cave16.toml",
        "assets/levels/intermission4.toml"
    ]

    TICK_RATE = 1 / 30
    PLAYER_MOVE_DELAY = 0.2
    IDLE_ANIMATIONS = ["player_wait", "player_idle_blink", "player_wait_blink"]
    MAX_LIVES = 3

    def __init__(self, config: Config, headless: bool = False, renderer=None):
        self.config = config
        self.level_index = 0
        self.level: Level | None = None
        self.running = True
        self.diamonds_collected = 0
        self.time_remaining = 0
        self.lives = self.MAX_LIVES
        self.game_over = False
        self.score = 0
        self.score_at_level_start = 0
        self.exit_open = False

        self.move_timer = 0.0
        self.player_animation = "player_idle"
        self.last_direction = "right"
        self.idle_timer = 0.0
        self.idle_threshold = 2.0
        self.is_moving = False

        self.level_complete = False
        self.level_end_time = 0.0
        self.level_end_delay = 2.0
        self.time_bonus_start = 0.0
        self.time_bonus_duration = 2.0
        self.time_bonus_done = False
        self.time_bonus_added = 0

        self.is_dying = False
        self.death_timer = 0.0
        self.death_duration = 1.5

        if headless:
            if renderer is None:
                class _HeadlessRenderer:
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

                renderer = _HeadlessRenderer()

            self.renderer = renderer
            self.keys = key.KeyStateHandler()
        else:
            pyglet.clock.schedule_interval(self.update, self.TICK_RATE)

            from game.gfx.renderer import Renderer
            self.renderer = Renderer(config, self)

            self.keys = key.KeyStateHandler()
            self.renderer.push_handlers(self.keys)

        self._load_level(self.LEVELS[self.level_index])

        if self.level is not None:
            self.level.renderer = self.renderer

        self.camera_pos = self._compute_camera_target()

    def run(self):
        pyglet.app.run(interval=0)

    def _load_level(self, path):
        if self.level is None:
            self.score_at_level_start = self.score
        else:
            self.score = self.score_at_level_start

        self.level = Level(path)
        self.time_remaining = self.level.time_limit
        self.diamonds_collected = 0
        self.idle_timer = 0.0
        self.last_direction = "right"
        self.exit_open = False

        self.level_complete = False
        self.level_end_timer = 0.0
        self.time_bonus_start = 0.0
        self.time_bonus_done = False
        self.time_bonus_added = 0

        self.restart_charge = 0.0
        self.restart_charge_time = 1.5
        self.restart_active = False

        self.score_at_level_start = self.score

        self.level.renderer = self.renderer
        self.renderer.set_level(self.level)

        self.level.on_player_killed = self._kill_player

        ex, ey = self.level.exit_x, self.level.exit_y
        if ex != -1 and ey != -1:
            exit_tile = self.level.grid[ey][ex]
            exit_tile.set_sprite("titanium_wall")
            self.renderer.update_tile_sprite(exit_tile)

    def update(self, dt):
        if self.level is None:
            return

        if self.game_over:
            self._update_restart_charge(dt)
            self._update_camera(dt)
            return

        if self.is_dying:
            self.death_timer += dt
            if self.death_timer >= self.death_duration:
                self._restart_level()
                self.is_dying = False
                self.death_timer = 0.0
            self._update_camera(dt)
            return

        if not self.level_complete:
            self.level.update(dt)

            if self.time_remaining > 0:
                self.time_remaining -= dt
                if self.time_remaining <= 0:
                    self.time_remaining = 0
                    self._kill_player()

            if not self.is_moving:
                self.idle_timer += dt
                if self.idle_timer >= self.idle_threshold:
                    idle_anim = random.choice(self.IDLE_ANIMATIONS)
                    self._set_player_animation(idle_anim)
                    self.idle_timer = 0.0
            else:
                self.is_moving = False

            self.move_timer += dt
            if self.move_timer >= self.PLAYER_MOVE_DELAY:
                self.move_timer = 0.0
                self._handle_player_input()
        else:
            self._update_level_complete(dt)

        self._update_restart_charge(dt)


        self._update_camera(dt)

    def _compute_camera_target(self):
        tile_px = 32 * self.config.get("render_scale", 2)
        player_x = (self.level.player_x + 0.5) * tile_px
        player_y = (self.level.height - self.level.player_y - 0.5) * tile_px

        level_width_px = self.level.width * tile_px
        level_height_px = self.level.height * tile_px

        view_w = self.renderer.width
        view_h = self.renderer.height

        desired_x = player_x - view_w * 0.5
        desired_y = player_y - view_h * 0.5

        ui_bar_px = 48 * self.config.get("render_scale", 2)

        if level_width_px <= view_w:
            clamped_x = (level_width_px - view_w) * 0.5
        else:
            max_x = level_width_px - view_w
            clamped_x = min(max(0, desired_x), max_x)

        usable_view_h = max(1, view_h - ui_bar_px)
        if level_height_px <= usable_view_h:
            clamped_y = (level_height_px - usable_view_h) * 0.5
        else:
            max_y = level_height_px - usable_view_h
            clamped_y = min(max(0, desired_y), max_y)

        return Vec3(clamped_x, clamped_y, 0)

    def _update_camera(self, dt):
        if self.level is None:
            return

        self.camera_pos = self._compute_camera_target()

    def on_key_press(self, symbol, modifiers):
        if self.game_over:
            return
        # if symbol == key.P:
        #     self.level_index = (self.level_index + 1) % len(self.LEVELS)
        #     self._load_level(self.LEVELS[self.level_index])
        # elif symbol == key.O:
        #     self.level_index = (self.level_index - 1) % len(self.LEVELS)
        #     self._load_level(self.LEVELS[self.level_index])

    def _set_player_animation(self, animation_name):
        if self.level is None or self.player_animation == animation_name:
            return

        self.player_animation = animation_name
        px = self.level.player_x
        py = self.level.player_y
        player_tile = self.level.grid[py][px]
        player_tile.set_sprite(animation_name)
        self.renderer.update_tile_sprite(player_tile)

    def _move_player(self, dx, dy):
        if self.level is None:
            return

        px = self.level.player_x
        py = self.level.player_y
        nx = px + dx
        ny = py + dy

        if not (0 <= nx < self.level.width and 0 <= ny < self.level.height):
            return

        target = self.level.grid[ny][nx]
        if target.type in (FIREFLY, BUTTERFLY):
            self._kill_player()
            return

        if not self.level.can_player_move_into(px, py, nx, ny):
            return

        if target.type == EXIT and not self.exit_open:
            return

        if target.type == DIAMOND:
            self.diamonds_collected += 1
            if self.diamonds_collected == self.level.diamonds_required:
                if not self.exit_open:
                    self.exit_open = True
                    ex, ey = self.level.exit_x, self.level.exit_y
                    if ex != -1 and ey != -1:
                        exit_tile = self.level.grid[ey][ex]
                        exit_tile.set_sprite("exit_blink")
                        self.renderer.update_tile_sprite(exit_tile)
                    self.renderer.start_flash()

            if self.diamonds_collected > self.level.diamonds_required:
                self.score += self.level.bonus_diamond_value
            else:
                self.score += self.level.diamond_value

        if target.type == EXIT and self.exit_open:
            self._finish_player_move(px, py, nx, ny, target, dx, dy)
            self.level_complete = True
            self.level_end_timer = 0.0
            self.time_bonus_done = False
            self.time_bonus_added = 0
            self.time_bonus_start = max(0.0, float(self.time_remaining))
            return

        self._finish_player_move(px, py, nx, ny, target, dx, dy)

    def _handle_player_input(self):
        if self.level is None:
            return

        dx, dy = 0, 0
        if self.keys[key.LEFT] or self.keys[key.A]:
            dx = -1
        elif self.keys[key.RIGHT] or self.keys[key.D]:
            dx = 1
        elif self.keys[key.UP] or self.keys[key.W]:
            dy = -1
        elif self.keys[key.DOWN] or self.keys[key.S]:
            dy = 1

        if dx != 0 or dy != 0:
            self._move_player(dx, dy)
        else:
            if self.player_animation.startswith("player_walk"):
                self._set_player_animation("player_idle")

    def _update_level_complete(self, dt):
        self.level_end_timer += dt

        if not self.time_bonus_done and self.time_bonus_start > 0.0:
            t = min(self.level_end_timer, self.time_bonus_duration)
            frac = t / self.time_bonus_duration if self.time_bonus_duration > 0.0 else 1.0

            remaining_time = max(0.0, self.time_bonus_start * (1.0 - frac))
            self.time_remaining = remaining_time

            total_drained = int(round(self.time_bonus_start - remaining_time))

            delta = total_drained - self.time_bonus_added
            if delta > 0:
                self.score += delta
                self.time_bonus_added = total_drained

            if t >= self.time_bonus_duration or remaining_time <= 0.0:
                self.time_remaining = 0.0
                self.time_bonus_done = True
                self.level_end_timer = 0.0

        elif self.time_bonus_done:
            if self.level_end_timer >= self.level_end_delay:
                self._goto_next_level()

    def _goto_next_level(self):
        self.level_index = (self.level_index + 1) % len(self.LEVELS)
        self.score_at_level_start = self.score
        self._load_level(self.LEVELS[self.level_index])

    def _finish_player_move(self, px, py, nx, ny, target, dx, dy):
        if dx < 0:
            self.last_direction = "left"
            self._set_player_animation("player_walk_left")
        elif dx > 0:
            self.last_direction = "right"
            self._set_player_animation("player_walk_right")
        else:
            self._set_player_animation(f"player_walk_{self.last_direction}")

        self.idle_timer = 0.0
        self.is_moving = True

        old_tile = self.level.grid[py][px]
        old_tile.set_type(EMPTY)
        target.set_type(PLAYER)
        target.set_sprite(self.player_animation)

        self.level.player_x = nx
        self.level.player_y = ny

        self.renderer.update_tile_sprite(old_tile)
        self.renderer.update_tile_sprite(target)

    def _restart_level(self):
        if self.lives > 0:
            self.lives -= 1

        if self.lives <= 0:
            self.game_over = True
            self.restart_charge = 0.0
            self.restart_active = False
            self.renderer.restart_darkness = 0.0
            return

        self.score = self.score_at_level_start

        self.restart_charge = 0.0
        self.restart_active = False
        self.renderer.restart_darkness = 0.0
        self._load_level(self.LEVELS[self.level_index])

    def _restart_game(self):
        self.game_over = False
        self.is_dying = False
        self.death_timer = 0.0

        self.level_index = 0
        self.lives = self.MAX_LIVES
        self.score = 0
        self.score_at_level_start = 0
        self.restart_charge = 0.0
        self.restart_active = False
        self.renderer.restart_darkness = 0.0

        self._load_level(self.LEVELS[self.level_index])

    def _update_restart_charge(self, dt):
        if self.level_complete:
            self.restart_charge = 0.0
            self.restart_active = False
            self.renderer.restart_darkness = 0.0
            return

        if self.keys[key.R]:
            self.restart_active = True
            self.restart_charge = min(
                self.restart_charge_time,
                self.restart_charge + dt
            )
            intensity = self.restart_charge / self.restart_charge_time
            self.renderer.restart_darkness = intensity

            if self.restart_charge >= self.restart_charge_time:
                if self.game_over:
                    self._restart_game()
                else:
                    self._restart_level()
        else:
            self.restart_active = False
            self.restart_charge = 0.0
            self.renderer.restart_darkness = 0.0

    def _kill_player(self):
        if self.level is None or self.is_dying or self.level_complete:
            return

        px = self.level.player_x
        py = self.level.player_y

        # explode 3x3 around player
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x = px + dx
                y = py + dy
                if 0 <= x < self.level.width and 0 <= y < self.level.height:
                    tile = self.level.grid[y][x]
                    tile.set_sprite("explosion")
                    self.renderer.update_tile_sprite(tile)

        self.is_dying = True
        self.death_timer = 0.0
