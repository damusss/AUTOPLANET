import noise
import random

from src.server import god
from src.object_data import TileOD


class NoiseSettings:
    def __init__(self, start_frequency, frequency_multiplier, persistence, octaves):
        self.start_frequency = start_frequency
        self.frequency_multiplier = frequency_multiplier
        self.persistence = persistence
        self.octaves = octaves

    def get_value(self, x, y):
        amplitude = 1
        frequency = self.start_frequency
        noise_sum = 0
        amplitude_sum = 0
        for _ in range(self.octaves):
            raw_noise = noise.pnoise2(x * frequency, y * frequency, octaves=1)
            noise_val = (raw_noise + 1) / 2
            noise_sum += noise_val * amplitude
            amplitude_sum += amplitude
            amplitude *= self.persistence
            frequency *= self.frequency_multiplier
        return noise_sum / amplitude_sum


class OreSettings:
    def __init__(self, noise_settings, value_is_block, name, min_height=0):
        self.noise: NoiseSettings = noise_settings
        self.value_is_block = value_is_block
        self.name = name
        self.min_height = min_height

    def get_value(self, wx, wy):
        return (
            self.noise.get_value(
                wx + god.world.seeds[self.name][0],
                -wy + god.world.seeds[self.name][1],
            )
            if wy >= self.min_height
            else 1
        )


SURFACE_NOISE = NoiseSettings(0.04, 1.2, 0.2, 5)

CAVES = OreSettings(NoiseSettings(0.04, 1.2, 0.5, 5), 0.45, "core")
IRON = OreSettings(NoiseSettings(0.02, 1.2, 0.5, 5), 0.4, "iron_ore")
COPPER = OreSettings(NoiseSettings(0.03, 1.2, 0.5, 5), 0.35, "copper_ore", 20)

SURFACE_LAYER_HEIGHT = 6
SURFACE_HEIGHT_MULT = 30

UNDERGROUND_HEIGHT = 150
MOLD_LAYER_HEIGHT = 10
DEEP_UNDERGROUND_HEIGHT = 100


def get_surface_height(wx):
    return -int(
        SURFACE_NOISE.get_value(
            wx + god.world.seeds["surface"],
            0,
        )
        * SURFACE_HEIGHT_MULT
    )


def nylium_biome_handler(rel_y, wx):
    tile_type = TileOD.objects.nylium
    if rel_y == 0:
        tile_type = TileOD.objects.nylium_surface
    return [tile_type.uid, 1, 0]


def underground_biome_handler(rel_y, wx):
    solid = 1
    ore_amount = 1000
    tile_type = TileOD.objects.core
    if CAVES.get_value(wx, rel_y) <= CAVES.value_is_block:
        solid = 0
    for ore in [IRON, COPPER]:
        if ore.get_value(wx, rel_y) <= ore.value_is_block:
            tile_type = TileOD.get(ore.name)
    return [tile_type.uid, solid, ore_amount]


def mold_layer_biome_handler(rel_y, wx):
    return [TileOD.objects.mold_patch.uid, 1, 1000]


def deep_underground_biome_handler(rel_y, wx):
    return [TileOD.objects.iron_ore.uid, 1, 1000]


def last_biome_handler(rel_y, wx):
    return [TileOD.objects.diamond_ore.uid, 1, 1000]


def get_biome_handler(wy, surface_height):
    if wy < surface_height:
        return None, 0
    rel_y = wy - surface_height
    for height, func in [
        (SURFACE_LAYER_HEIGHT, nylium_biome_handler),
        (UNDERGROUND_HEIGHT, underground_biome_handler),
        (MOLD_LAYER_HEIGHT, mold_layer_biome_handler),
        (DEEP_UNDERGROUND_HEIGHT, deep_underground_biome_handler),
    ]:
        if rel_y < height:
            return func, rel_y
        rel_y -= height
    return last_biome_handler, rel_y


def get_random_seed():
    return random.randint(0, int(10e6))
