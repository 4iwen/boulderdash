"""Tile types, flags and tile state"""

from enum import IntFlag, auto

import pyglet

EMPTY = 0
DIRT = 1
ROCK = 2
DIAMOND = 3
WALL = 4
PLAYER = 5
EXIT = 6
TITANIUM_WALL = 7
MAGIC_WALL = 8
AMOEBA = 9
FIREFLY = 10
BUTTERFLY = 11

TILE_SPRITES = {
    EMPTY: "empty",
    DIRT: "dirt",
    ROCK: "boulder",
    DIAMOND: "diamond",
    WALL: "wall",
    PLAYER: "player_idle",
    EXIT: "exit",
    TITANIUM_WALL: "titanium_wall",
    MAGIC_WALL: "magic_wall",
    AMOEBA: "amoeba",
    FIREFLY: "firefly",
    BUTTERFLY: "butterfly"
}


class TileFlags(IntFlag):
    NONE = 0
    PUSHABLE = auto()
    CONSUMABLE = auto()
    CAN_FALL = auto()
    EXPLODABLE = auto()
    PICKUPABLE = auto()
    ROUNDED = auto()
    SOLID = auto()


TILE_TYPE_FLAGS: dict[int, TileFlags] = {
    EMPTY: TileFlags.NONE,
    DIRT: TileFlags.CONSUMABLE,
    ROCK: (
        TileFlags.PUSHABLE
        | TileFlags.CAN_FALL
        | TileFlags.ROUNDED
        | TileFlags.SOLID
        | TileFlags.EXPLODABLE
    ),
    DIAMOND: (
        TileFlags.PICKUPABLE
        | TileFlags.CAN_FALL
        | TileFlags.ROUNDED
        | TileFlags.SOLID
        | TileFlags.EXPLODABLE
    ),
    WALL: TileFlags.SOLID,
    PLAYER: TileFlags.NONE,
    EXIT: TileFlags.SOLID,
    TITANIUM_WALL: TileFlags.SOLID,
    MAGIC_WALL: TileFlags.SOLID,
    AMOEBA: TileFlags.EXPLODABLE,
    FIREFLY: TileFlags.EXPLODABLE | TileFlags.SOLID,
    BUTTERFLY: TileFlags.EXPLODABLE | TileFlags.SOLID,
}


class Tile:
    def __init__(self, tile_type: int):
        self.type = tile_type
        self.sprite_name = TILE_SPRITES.get(tile_type, "empty")
        self.sprite: pyglet.sprite.Sprite | None = None
        self.falling: bool = False
        self.flags: TileFlags = TILE_TYPE_FLAGS.get(tile_type, TileFlags.NONE)

        self.enemy_dir: int = 0
        self.enemy_wait: int = 0
        self.enemy_paused: bool = False

    def set_type(self, tile_type: int):
        self.type = tile_type
        self.sprite_name = TILE_SPRITES.get(tile_type, "empty")
        self.falling = False
        self.flags = TILE_TYPE_FLAGS.get(tile_type, TileFlags.NONE)

        if tile_type in (FIREFLY, BUTTERFLY):
            self.enemy_dir = getattr(self, "enemy_dir", 0)
            self.enemy_wait = 0
            self.enemy_paused = False
        else:
            self.enemy_dir = 0
            self.enemy_wait = 0
            self.enemy_paused = False

    def set_sprite(self, sprite_name: str):
        self.sprite_name = sprite_name

    def is_pushable(self) -> bool:
        return bool(self.flags & TileFlags.PUSHABLE)

    def is_pickupable(self) -> bool:
        return bool(self.flags & TileFlags.PICKUPABLE)

    def can_fall(self) -> bool:
        return bool(self.flags & TileFlags.CAN_FALL)

    def is_explodable(self) -> bool:
        return bool(self.flags & TileFlags.EXPLODABLE)

    def is_rounded(self) -> bool:
        return bool(self.flags & TileFlags.ROUNDED)

    def is_consumable(self) -> bool:
        return bool(self.flags & TileFlags.CONSUMABLE)

    def is_solid(self) -> bool:
        return bool(self.flags & TileFlags.SOLID)

    def add_flag(self, flag: TileFlags):
        self.flags |= flag

    def remove_flag(self, flag: TileFlags):
        self.flags &= ~flag
