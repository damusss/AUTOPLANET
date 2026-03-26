import noise

from src import constants
from src.server import god


class NoiseSettings:
    def __init__(self, start_frequency, frequency_multiplier, persistence, octaves):
        self.start_frequency = start_frequency
        self.frequency_multiplier = frequency_multiplier
        self.persistence = persistence
        self.octaves = octaves


SURFACE_NOISE = NoiseSettings(0.04, 1.2, 0.2, 5)
CAVE_NOISE = NoiseSettings(0.04, 1.2, 0.5, 5)


def get_surface_height(wx):
    return -int(
        get_noise_value(
            wx + god.world.seed,
            0,
            SURFACE_NOISE,
        )
        * constants.HEIGHT_MULT
    )


def get_noise_value(x, y, settings: NoiseSettings):
    amplitude = 1
    frequency = settings.start_frequency
    noise_sum = 0
    amplitude_sum = 0
    for i in range(settings.octaves):
        raw_noise = noise.pnoise2(x * frequency, y * frequency, octaves=1)
        noise_val = (raw_noise + 1) / 2
        noise_sum += noise_val * amplitude
        amplitude_sum += amplitude
        amplitude *= settings.persistence
        frequency *= settings.frequency_multiplier

    return noise_sum / amplitude_sum
