import random

import pygame

from src import shared
from src import constants
from src.server import god
from src.server import terrain
from src.object_data import Star, Dust, BigStar, BlackHole, TileOD
from src.server.drop import Drop
from src.server.energy import EnergyProvider


class Chunk:
    def __init__(self, chunk_key, chunk_pos):
        self.chunk_key = chunk_key
        self.chunk_pos = pygame.Vector2(chunk_pos)
        self.world_topleft = shared.get_chunk_world_pos(self.chunk_pos)
        self.world_rect = pygame.FRect(
            self.world_topleft, (constants.CHUNK_SIZE, constants.CHUNK_SIZE)
        )
        self.refresh_pending = False
        self.energy_providers: set[EnergyProvider] = set()
        self.moving_building_ids = set()
        self.building_ids = set()
        self.building_floor_hitboxes: list[pygame.FRect] = []
        self.building_ids_table: dict[tuple[int, int], str] = {}
        self.drops: list[Drop] = []
        self.loaded_client_players = []
        self.tile_hitboxes: list[pygame.FRect] = []
        self.tile_hitboxes_table: dict[tuple[int, int], pygame.FRect] = {}
        self.lights = []  # (cx, cy, radius, intensity, rgb)
        self.stars = []  # (cx, cy, size)
        self.dusts = []  # (cx, cy, size, rgb)
        self.big_star = None  # (cx, cy, size, type index (-1 = black hole))
        self.tiles_mat: list[list] = (
            [None] * constants.CHUNK_SIZE * constants.CHUNK_SIZE
        )  # (type ID, solid 1|0, ore amount)
        self.generate()

    @property
    def buildings(self):
        return (god.world.buildings[bid] for bid in self.building_ids)

    def get_energy_providers_for_rect(self, rect) -> list[EnergyProvider]:
        providers = []
        for provider in self.energy_providers:
            if shared.rect_collide_circle(rect, provider.center, provider.radius):
                providers.append(provider)
        return providers

    def refresh(self):
        if self.refresh_pending:
            return
        if self.chunk_key not in god.world.refresh_queued_chunks:
            god.world.refresh_queued_chunks.add(self.chunk_key)

    def generate(self):
        self.generate_tiles()
        if self.chunk_pos.y <= 2:
            self.generate_stars()
        if self.chunk_pos.y <= 0:
            self.generate_dusts()
            self.generate_big_star()

    def generate_tiles(self):
        left = terrain.get_surface_height(-1 + self.world_topleft.x)
        current = terrain.get_surface_height(0 + self.world_topleft.x)
        right = terrain.get_surface_height(1 + self.world_topleft.x)
        for cx in range(constants.CHUNK_SIZE):
            height = current
            # erase lonely 1-wide tiles at the top of the heels (NOT WORKING)
            if left == right and (current - right) == 1:
                height = right
            left = height
            current = right
            right = terrain.get_surface_height(cx + 2 + self.world_topleft.x)
            for cy in range(constants.CHUNK_SIZE):
                wy = self.world_topleft.y + cy
                biome_handler, rel_y = terrain.get_biome_handler(wy, height)
                if biome_handler is not None:
                    tile_data = biome_handler(rel_y, cx + self.world_topleft.x)
                    if tile_data is not None:
                        self.tiles_mat[cy * constants.CHUNK_SIZE + cx] = tile_data
                        if tile_data[1]:
                            rect = pygame.FRect(
                                self.world_topleft.x + cx,
                                self.world_topleft.y + cy,
                                1,
                                1,
                            )
                            self.tile_hitboxes.append(rect)
                            self.tile_hitboxes_table[(cx, cy)] = rect

    def generate_stars(self):
        for cx in range(constants.CHUNK_SIZE):
            for cy in range(constants.CHUNK_SIZE):
                tile = self.tiles_mat[cy * constants.CHUNK_SIZE + cx]
                if tile is not None:
                    continue
                if random.uniform(0, 1) <= Star.chance:
                    sx = random.uniform(-0.1, 1.1) + cx
                    sy = random.uniform(-0.1, 1.1) + cy
                    ss = random.uniform(*Star.size_range)
                    self.stars.append((sx, sy, ss))

    def generate_dusts(self):
        for i in range(random.randint(*Dust.num_range)):
            size = random.uniform(*Dust.size_range)
            x, y = (
                random.uniform(0, constants.CHUNK_SIZE),
                random.uniform(0, constants.CHUNK_SIZE),
            )
            color = pygame.Color(Dust.gradient_a).lerp(
                Dust.gradient_b, random.uniform(0, 1)
            )
            self.dusts.append(
                (
                    x - size / 2,
                    y - size / 2,
                    size,
                    (color.r, color.g, color.b),
                )
            )

    def generate_big_star(self):
        if random.uniform(0, 1) <= BigStar.chance:
            boundl, boundr = (
                constants.CHUNK_SIZE / 6,
                constants.CHUNK_SIZE - constants.CHUNK_SIZE / 6,
            )
            self.big_star = (
                random.uniform(boundl, boundr),
                random.uniform(boundl, boundr),
                random.uniform(*BigStar.size_range),
                random.randint(0, len(BigStar.colors) - 1),
            )
        else:
            if self.chunk_pos.y > -4 and abs(self.chunk_pos.x) > 10:
                if random.uniform(0, 1) < BlackHole.chance:
                    self.big_star = (
                        constants.CHUNK_SIZE / 2,
                        constants.CHUNK_SIZE / 2,
                        random.uniform(*BlackHole.size_range),
                        -1,
                    )

    def get_tile(self, tile_pos):
        return self.tiles_mat[tile_pos[1] * constants.CHUNK_SIZE + tile_pos[0]]

    def get_tile_index(self, tile_pos):
        return tile_pos[1] * constants.CHUNK_SIZE + tile_pos[0]

    def get_client_data(self):
        return {
            "key": self.chunk_key,
            "stars": self.stars,
            "dusts": self.dusts,
            "big_star": self.big_star,
            "tiles": self.tiles_mat,
            "lights": self.lights,
            "buildings": [
                god.world.buildings[bid].get_client_data()
                for bid in self.building_ids
                if bid in god.world.buildings
            ],
            "energy": sum(
                (
                    [
                        conn.get_client_data()
                        for conn in god.world.buildings[bid].ext.energy_conns[
                            : constants.MAX_CLIENT_CONNECTIONS_PER_BUILDING
                        ]
                    ]
                    for bid in self.building_ids
                    if bid in god.world.buildings
                ),
                start=[],
            ),
        }
