import pyglet
from pyglet.image import AnimationFrame, Animation, ImageDataRegion
from pyglet.image import ImageData


class SpriteAtlas:
    def __init__(self, path, tile_size=16):
        self.image = pyglet.image.load(path)
        self.tile_size = tile_size

        self.grid = pyglet.image.ImageGrid(
            self.image,
            rows=self.image.height // tile_size,
            columns=self.image.width // tile_size
        )

        self.entries = {}
        self._base_entries = {}
        self.colors = {}

    def sprite(self, name, row, col):
        img = self.grid[row, col]
        self._base_entries[name] = img
        self.entries[name] = img

    def animation(self, name, frames, duration=1 / 30):
        base_frames = [AnimationFrame(self.grid[row, col], duration) for (row, col) in frames]
        base_anim = Animation(base_frames)
        self._base_entries[name] = base_anim
        self.entries[name] = Animation([AnimationFrame(f.image, f.duration) for f in base_frames])

    def color(self, name, color: tuple[int, int, int]):
        self.colors[name] = (color[0], color[1], color[2], 255)

    def __getitem__(self, key):
        return self.entries[key]

    def _deep_copy_image(self, image):
        img_data = image.get_image_data()
        img_data.format = "RGBA"
        img_data.pitch = img_data.width * 4
        raw = img_data.get_bytes(img_data.format, img_data.pitch)

        new_img = ImageData(image.width, image.height, "RGBA", bytes(raw), pitch=img_data.pitch)
        return new_img.get_region(0, 0, image.width, image.height)

    def reset_colors(self):
        restored = {}
        for name, base in self._base_entries.items():
            if isinstance(base, Animation):
                frames = []
                for frame in base.frames:
                    img_copy = self._deep_copy_image(frame.image)
                    frames.append(AnimationFrame(img_copy, frame.duration))
                restored[name] = Animation(frames)
            else:
                restored[name] = self._deep_copy_image(base)
        self.entries = restored

    def remap_colors(self, src_to_dst: dict[tuple[int, int, int, int], tuple[int, int, int, int]]):


        for name, entry in list(self.entries.items()):
            if isinstance(entry, Animation):
                for frame in entry.frames:
                    self._recolor_image(frame.image, src_to_dst)
            elif isinstance(entry, ImageDataRegion):
                self._recolor_image(entry, src_to_dst)

    def _recolor_image(self, image, src_to_dst):
        img_data = image.get_image_data()
        img_data.format = "RGBA"
        img_data.pitch = img_data.width * 4
        raw = bytearray(img_data.get_bytes(img_data.format, img_data.pitch))

        w = image.width
        h = image.height
        bpp = 4

        src_keys = set(src_to_dst.keys())

        for y in range(h):
            base = y * w * bpp
            for x in range(w):
                i = base + x * bpp
                rgba = (raw[i], raw[i + 1], raw[i + 2], raw[i + 3])
                if rgba in src_keys:
                    dr, dg, db, da = src_to_dst[rgba]
                    raw[i] = dr
                    raw[i + 1] = dg
                    raw[i + 2] = db
                    raw[i + 3] = da

        img_data.set_bytes("RGBA", img_data.pitch, bytes(raw))
