import math
import pyglet
from pyglet.window import FPSDisplay
from pyglet.gl.gl import GL_NEAREST
from pyglet.math import Mat4, Vec3
from game.cfg.config import Config
from game.gfx.spriteatlas import SpriteAtlas
from game.game import Game


class Renderer(pyglet.window.Window):
    def __init__(self, config: Config, game: Game):
        self.game = game
        self.set_handlers(game)

        # Load font
        pyglet.font.add_file("assets/fonts/Boulder Dash 6128.ttf")

        # Some settings
        pyglet.options.dpi_scaling = "scaled"
        pyglet.image.Texture.default_min_filter = GL_NEAREST
        pyglet.image.Texture.default_mag_filter = GL_NEAREST

        # Create window
        width = config.get("window_width", 640)
        height = config.get("window_height", 400)
        self.show_fps = config.get("show_fps", False)
        super().__init__(width, height, "Boulder Dash", resizable=True, vsync=False)

        # Load sprites and colors
        self.render_scale = config.get("render_scale", 2)
        self.tile_size = 32
        self.atlas = SpriteAtlas("assets/sprites/spritesheet.png", tile_size=self.tile_size)
        self._load_sprites()
        self._load_colors()

        self.sprite_batch = pyglet.graphics.Batch()

        self.fps_display = FPSDisplay(self, color=(0, 255, 0, 255))

        # Flash overlay state
        self.flash_timer = 0.0
        self.flash_duration = 25 * Game.TICK_RATE

        self.restart_darkness = 0.0

    def start_flash(self, duration: float | None = None):
        """Trigger a full-screen white flash for a short duration."""
        if duration is None:
            duration = self.flash_duration
        self.flash_timer = max(self.flash_timer, duration)

    def on_draw(self):
        self.clear()
        self._draw_level()
        self._draw_ui()
        self._draw_overlays()

        if self.show_fps:
            self.fps_display.draw()

    def _load_sprites(self):
        # UI
        self.atlas.sprite("hp_icon", 11, 7)

        # Static sprites
        self.atlas.sprite("titanium_wall", 5, 1)
        self.atlas.sprite("exit", 5, 2)
        self.atlas.sprite("wall", 5, 3)
        self.atlas.sprite("dirt", 4, 1)
        self.atlas.sprite("boulder", 4, 0)
        self.atlas.sprite("empty", 5, 0)
        self.atlas.sprite("player_idle", 11, 0)

        # Animated sprites
        self.atlas.animation("player_idle_blink", [
            (10, 0), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)
        ])
        self.atlas.animation("player_wait", [
            (9, 0), (9, 1), (9, 2), (9, 3), (9, 4), (9, 5), (9, 6), (9, 7)
        ])
        self.atlas.animation("player_wait_blink", [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6), (8, 7)
        ])
        self.atlas.animation("player_walk_left", [
            (7, 0), (7, 1), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (7, 7)
        ])
        self.atlas.animation("player_walk_right", [
            (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7)
        ])
        self.atlas.animation("exit_blink", [
            (5, 1), (5, 2)
        ], 4 / 15)
        self.atlas.animation("diamond", [
            (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7)
        ])
        self.atlas.animation("magic_wall", [
            (5, 4), (5, 5), (5, 6), (5, 7)
        ], 1 / 15)
        self.atlas.animation("amoeba", [
            (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7)
        ])
        self.atlas.animation("firefly", [
            (2, 0), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7)
        ])
        self.atlas.animation("butterfly", [
            (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7)
        ])
        self.atlas.animation("explosion", [
            (11, 1), (11, 2), (11, 3)
        ], 5 / 9)
        self.atlas.animation("diamond_explosion", [
            (4, 3), (4, 4), (4, 5), (4, 6), (4, 7)
        ], 1 / 20)

    def _load_colors(self):
        # Commodore 64 palette
        self.atlas.color("black", (0, 0, 0))
        self.atlas.color("white", (255, 255, 255))
        self.atlas.color("red", (136, 0, 0))
        self.atlas.color("cyan", (170, 255, 238))
        self.atlas.color("purple", (204, 68, 204))
        self.atlas.color("green", (0, 204, 85))
        self.atlas.color("blue", (0, 0, 170))
        self.atlas.color("yellow", (238, 238, 119))
        self.atlas.color("orange", (221, 136, 85))
        self.atlas.color("brown", (102, 68, 0))
        self.atlas.color("lightred", (255, 119, 119))
        self.atlas.color("gray1", (51, 51, 51))
        self.atlas.color("gray2", (119, 119, 119))
        self.atlas.color("lightgreen", (170, 255, 102))
        self.atlas.color("lightblue", (0, 136, 255))
        self.atlas.color("lightgray", (187, 187, 187))

    def set_level(self, level):
        self.sprite_batch = pyglet.graphics.Batch()

        self.atlas.reset_colors()
        self.atlas.remap_colors(
            {
                self.atlas.colors["gray1"]: self.atlas.colors[level.colors.get("background1", "gray1")],
                self.atlas.colors["brown"]: self.atlas.colors[level.colors.get("background2", "brown")],
                self.atlas.colors["white"]: self.atlas.colors[level.colors.get("foreground", "white")]
            }
        )

        for y, row in enumerate(level.grid):
            for x, tile in enumerate(row):
                img = self.atlas.entries[tile.sprite_name]

                screen_x = x * self.tile_size * self.render_scale
                screen_y = (level.height - y - 1) * self.tile_size * self.render_scale

                sprite = pyglet.sprite.Sprite(
                    img,
                    x=screen_x,
                    y=screen_y,
                    batch=self.sprite_batch
                )
                sprite.scale = self.render_scale
                tile.sprite = sprite

    def update_tile_sprite(self, tile):
        if tile.sprite is None:
            return

        new_img = self.atlas.entries[tile.sprite_name]
        if tile.sprite.image is not new_img:
            tile.sprite.image = new_img

    def _draw_level(self):
        self.view = Mat4.from_translation(Vec3(-self.game.camera_pos.x, -self.game.camera_pos.y, 0))
        self.sprite_batch.draw()

    def _draw_ui(self):
        batch = pyglet.graphics.Batch()

        self.view = Mat4()

        font_name = "BoulderDash6128"
        base_font_size = 28
        base_bar_height = 48
        font_size = base_font_size * self.render_scale
        bar_height = base_bar_height * self.render_scale
        y_pos = self.height - (bar_height // 2)

        self.status_bar = pyglet.shapes.Rectangle(
            0, self.height - bar_height,
            self.width, bar_height,
            color=(0, 0, 0),
            batch=batch
        )

        padding = int(8 * self.render_scale)

        hp_icon = self.atlas.entries["hp_icon"]
        hp_sprites = []
        icon_width = self.tile_size * self.render_scale
        icon_spacing = int(4 * self.render_scale)
        max_lives = 3

        for i in range(self.game.lives):
            hp_sprite = pyglet.sprite.Sprite(
                hp_icon,
                x=padding + i * (icon_width + icon_spacing),
                y=y_pos - icon_width // 2,
                batch=batch
            )
            hp_sprite.scale = self.render_scale
            hp_sprites.append(hp_sprite)

        total_hp_width = max_lives * icon_width + (max_lives - 1) * icon_spacing

        labels = []

        diamonds_required_text = f"{self.game.level.diamonds_required:02d}"
        diamonds_text = f"{self.game.diamonds_collected:02d}"
        time_text = f"{math.ceil(self.game.time_remaining):03d}"
        score_text = f"{self.game.score:06d}"

        labels.append(pyglet.text.Label(
            diamonds_required_text,
            font_name=font_name,
            font_size=font_size,
            x=0, y=y_pos,
            anchor_x="left", anchor_y="center",
            color=(255, 255, 0, 255),
            batch=batch
        ))
        labels.append(pyglet.text.Label(
            diamonds_text,
            font_name=font_name,
            font_size=font_size,
            x=0, y=y_pos,
            anchor_x="left", anchor_y="center",
            color=(255, 255, 255, 255),
            batch=batch
        ))
        labels.append(pyglet.text.Label(
            time_text,
            font_name=font_name,
            font_size=font_size,
            x=0, y=y_pos,
            anchor_x="left", anchor_y="center",
            color=(0, 255, 0, 255),
            batch=batch
        ))
        labels.append(pyglet.text.Label(
            score_text,
            font_name=font_name,
            font_size=font_size,
            x=0, y=y_pos,
            anchor_x="left", anchor_y="center",
            color=(255, 255, 255, 255),
            batch=batch
        ))

        widths = [int(label.content_width) for label in labels]
        total_width = sum(widths) + total_hp_width
        available = self.width - 2 * padding
        n = len(labels) + 1

        if n > 1:
            gap = int((available - total_width) / (n - 1)) if available > total_width else padding
            gap = max(padding, gap)
        else:
            gap = 0

        for i in range(self.game.lives):
            hp_sprite = pyglet.sprite.Sprite(
                hp_icon,
                x=padding + i * (icon_width + icon_spacing),
                y=y_pos - icon_width // 2,
                batch=batch
            )
            hp_sprite.scale = self.render_scale
            hp_sprites.append(hp_sprite)

        x_pos = padding + total_hp_width + gap
        for label in labels:
            label.x = int(x_pos)
            x_pos += int(label.content_width) + gap

        batch.draw()

    def _draw_overlays(self):
        if self.flash_timer > 0.0:
            overlay = pyglet.shapes.Rectangle(
                0,
                0,
                self.width,
                self.height,
                color=(255, 255, 255)
            )
            overlay.opacity = 127
            overlay.draw()
            self.flash_timer = max(0.0, self.flash_timer - Game.TICK_RATE)

        if self.restart_darkness > 0.0:
            darkness = int(255 * self.restart_darkness)
            overlay = pyglet.shapes.Rectangle(
                0,
                0,
                self.width,
                self.height,
                color=(0, 0, 0)
            )
            overlay.opacity = darkness
            overlay.draw()

        if getattr(self.game, "game_over", False):
            overlay = pyglet.shapes.Rectangle(
                0,
                0,
                self.width,
                self.height,
                color=(0, 0, 0)
            )
            overlay.opacity = 220
            overlay.draw()

            font_name = "BoulderDash6128"

            title_size = int(48 * self.render_scale)
            score_size = int(20 * self.render_scale)
            hint_size = int(18 * self.render_scale)
            gap = int(12 * self.render_scale)

            center_y = self.height // 2
            stack_height = title_size + gap + score_size + gap + hint_size
            top_y = center_y + stack_height // 2

            title_y = top_y - title_size // 2
            score_y = top_y - title_size - gap - score_size // 2
            hint_y = top_y - title_size - gap - score_size - gap - hint_size // 2

            title = pyglet.text.Label(
                "GAME OVER",
                font_name=font_name,
                font_size=title_size,
                x=self.width // 2,
                y=title_y,
                anchor_x="center",
                anchor_y="center",
                color=(255, 255, 255, 255)
            )
            title.draw()

            score_label = pyglet.text.Label(
                f"Final score: {getattr(self.game, 'score', 0)}",
                font_name=font_name,
                font_size=score_size,
                x=self.width // 2,
                y=score_y,
                anchor_x="center",
                anchor_y="center",
                color=(255, 255, 255, 255)
            )
            score_label.draw()

            hint = pyglet.text.Label(
                "Hold R to restart",
                font_name=font_name,
                font_size=hint_size,
                x=self.width // 2,
                y=hint_y,
                anchor_x="center",
                anchor_y="center",
                color=(255, 255, 255, 255)
            )
            hint.draw()
