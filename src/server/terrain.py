import noise
import random

from src.server import god
from src.object_data import TileOD, VegetationOD

class NoiseSettings:
    def __init__(
        self,
        start_frequency,
        frequency_multiplier,
        persistence,
        octaves,
        stretch=(1, 1),
    ):
        self.start_frequency = start_frequency
        self.frequency_multiplier = frequency_multiplier
        self.persistence = persistence
        self.octaves = octaves
        self.stretch = stretch

    def get_value(self, x, y):
        amplitude = 1
        frequency = self.start_frequency
        noise_sum = 0
        amplitude_sum = 0
        for _ in range(self.octaves):
            raw_noise = noise.pnoise2(
                x * (frequency / self.stretch[0]),
                y * (frequency / self.stretch[1]),
                octaves=1,
            )
            noise_val = (raw_noise + 1) / 2
            noise_sum += noise_val * amplitude
            amplitude_sum += amplitude
            amplitude *= self.persistence
            frequency *= self.frequency_multiplier
        return noise_sum / amplitude_sum


DISTRIBUTION_SETTINGS = []


class DistributionSettings:
    def __init__(self, noise_settings, value_is_block, name, min_height=0):
        self.noise: NoiseSettings = (
            noise_settings
            if isinstance(noise_settings, NoiseSettings)
            else NoiseSettings(*noise_settings)
        )
        self.value_is_block = value_is_block
        self.name = name
        self.min_height = min_height
        DISTRIBUTION_SETTINGS.append(self)

    def get_value(self, wx, wy):
        return (
            self.noise.get_value(
                wx + god.world.seeds[self.name][0],
                -wy + god.world.seeds[self.name][1],
            )
            if wy >= self.min_height
            else 1
        )

    def is_here_block(self, wx, wy):
        return self.get_value(wx, wy) <= self.value_is_block


SURFACE_NOISE = NoiseSettings(0.04, 1.2, 0.2, 5)

CAVES = DistributionSettings((0.04, 1.2, 0.5, 5), 0.45, "core")
IRON = DistributionSettings((0.02, 1.2, 0.5, 5), 0.38, "iron_ore", 5)
COPPER = DistributionSettings((0.03, 1.2, 0.5, 5), 0.35, "copper_ore", 20)
MOLD = DistributionSettings((0.047, 2.0, 0.4, 3), 0.36, "mold", 15)
AMMONIA = DistributionSettings(
    (0.06, 1.5, 0.5, 4, (1, 4.0)), 0.35, "ammonia_deposit", 25
)

ISLAND_NOISE = NoiseSettings(
    start_frequency=0.048,
    frequency_multiplier=2.0,
    persistence=0.12,
    octaves=2,
)
ISLANDS_A = DistributionSettings(ISLAND_NOISE, 0.80, "islands_a")
ISLANDS_B = DistributionSettings(ISLAND_NOISE, 0.80, "islands_b")

OXYGEN_PLANT = DistributionSettings((0.43, 1, 1, 1), 0.33, "oxygen_plant")
LIGHT_TREE = DistributionSettings((0.43, 1, 1, 1), 0.24, "light_tree")
NYLIUM_GRASS = DistributionSettings((0.15, 2, 0.5, 2), 0.55, "nylium_grass")
FLOWERS = DistributionSettings((0.25, 2, 0.5, 2), 0.38, "flowers")
CACTUS = DistributionSettings((0.15, 2, 0.5, 2), 0.47, "cactus")
CAVE_BULB = DistributionSettings((0.12, 2, 0.4, 2), 0.32, "cave_bulb")
CAVE_BLOOM = DistributionSettings((0.12, 2, 0.5, 2), 0.28, "cave_bloom")

ISLANDS_LAYER_HEIGHT = 80
ISLANDS_PAUSE_HEIGHT = 11
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


def island_is_block(rel_y, wx):
    if rel_y <= ISLANDS_PAUSE_HEIGHT:
        return False
    val_a = ISLANDS_A.get_value(wx, rel_y)
    val_b = ISLANDS_B.get_value(wx, rel_y)
    combined_noise = val_a + val_b
    return combined_noise <= ISLANDS_A.value_is_block


def islands_biome_handler(rel_y, wx, abs_y):
    abs_rel_y = abs(rel_y)
    if abs_rel_y <= ISLANDS_PAUSE_HEIGHT:
        return None, None

    if island_is_block(abs_rel_y, wx):
        is_block_top = island_is_block(abs_rel_y + 1, wx)
        is_block_bottom = island_is_block(abs_rel_y - 1, wx)
        is_block_left = island_is_block(abs_rel_y, wx - 1)
        is_block_right = island_is_block(abs_rel_y, wx + 1)

        if not is_block_top and not is_block_bottom:
            return None, None
        if not is_block_left and not is_block_right:
            return None, None

        tile_type = TileOD.objects.nylium
        plant_data = None

        if not is_block_top or abs_rel_y + 1 > ISLANDS_LAYER_HEIGHT:
            tile_type = TileOD.objects.nylium_surface
            if OXYGEN_PLANT.is_here_block(wx, abs_rel_y):
                plant_data = [wx, abs_y - 1, VegetationOD.objects.oxygen_plant]
            elif CACTUS.is_here_block(wx, abs_rel_y):
                plant_data = [wx, abs_y - 1, VegetationOD.objects.cactus]

        return [tile_type.uid, 1, 0], plant_data
    return None, None


def nylium_biome_handler(rel_y, wx, abs_y):
    tile_type = TileOD.objects.nylium
    plant_data = None
    if rel_y == 0:
        tile_type = TileOD.objects.nylium_surface
        if LIGHT_TREE.is_here_block(wx, rel_y):
            plant_data = [wx, abs_y - 1, VegetationOD.objects.light_tree]
        elif FLOWERS.is_here_block(wx, rel_y):
            plant_data = [wx, abs_y - 1, VegetationOD.objects.flowers]
        elif NYLIUM_GRASS.is_here_block(wx, rel_y):
            plant_data = [wx, abs_y - 1, VegetationOD.objects.nylium_grass]
    return [tile_type.uid, 1, 0], plant_data


def underground_biome_handler(rel_y, wx, abs_y):
    solid = 1
    ore_amount = 1000
    tile_type = TileOD.objects.core
    plant_data = None
    if CAVES.is_here_block(wx, rel_y):
        solid = 0
    for ore in [IRON, AMMONIA, COPPER]:
        if ore.is_here_block(wx, rel_y):
            tile_type = TileOD.get(ore.name)
    if solid == 0 and tile_type == TileOD.objects.core:
        if CAVE_BLOOM.is_here_block(wx, rel_y):
            plant_data = [wx, abs_y, VegetationOD.objects.cave_bloom]
        elif CAVE_BULB.is_here_block(wx, rel_y):
            plant_data = [wx, abs_y, VegetationOD.objects.cave_bulb]
    if solid == 1 and MOLD.is_here_block(wx, rel_y):
        tile_type = TileOD.objects.mold_patch
    return [tile_type.uid, solid, ore_amount], plant_data


def mold_layer_biome_handler(rel_y, wx, abs_y):
    return [TileOD.objects.mold_patch.uid, 1, 1000], None


def deep_underground_biome_handler(rel_y, wx, abs_y):
    return [TileOD.objects.iron_ore.uid, 1, 1000], None


def last_biome_handler(rel_y, wx, abs_y):
    return [TileOD.objects.diamond_ore.uid, 1, 1000], None


def get_biome_handler(wy, surface_height):
    rel_y = wy - surface_height
    if rel_y < 0:
        if abs(rel_y) > ISLANDS_LAYER_HEIGHT:
            return None, 0
        return islands_biome_handler, rel_y
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


def get_random_2d_seed():
    return (get_random_seed(), get_random_seed())
