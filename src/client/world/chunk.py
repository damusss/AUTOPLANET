import threading

import pygame

from src import constants
from src.client import god
from src.object_data import BigStar, BlackHole, TileOD
from src.client.rendering import (
    MeshRenderingLayer,
    TextureRenderingLayer,
)

if constants.NEW_RENDER:
    from pygame._render import Texture, GeometryMesh
else:
    from pygame._sdl2 import Texture


class QuadsMesh:
    def __init__(self):
        self.vertices = []
        self.indices = []
        self.quad_count = 0

    def add(self, topleft, size, color):
        topleft = pygame.Vector2(topleft)
        self.vertices += [
            (topleft, color, (0, 0)),
            ((topleft.x + size, topleft.y), color, (1, 0)),
            ((topleft + pygame.Vector2(size, size), color, (1, 1))),
            ((topleft.x, topleft.y + size), color, (0, 1)),
        ]
        self.indices += [
            self.quad_count + 0,
            self.quad_count + 1,
            self.quad_count + 2,
            self.quad_count + 2,
            self.quad_count + 3,
            self.quad_count + 0,
        ]
        self.quad_count += 4


class LightData:
    def __init__(self, world_pos, radius, intensity, color):
        self.world_pos = world_pos
        self.radius = radius
        self.intensity = intensity
        self.color = color


class Chunk:
    def __init__(self, data):
        self.loaded = True
        self.chunk_key = data["key"]
        self.chunk_pos = pygame.Vector2(
            [float(val) for val in self.chunk_key.split(";")]
        )
        self.world_topleft = pygame.Vector2(
            self.chunk_pos.x * constants.CHUNK_SIZE - constants.CHUNK_SIZE / 2,
            self.chunk_pos.y * constants.CHUNK_SIZE - constants.CHUNK_SIZE / 2,
        )
        self.world_rect = pygame.FRect(
            self.world_topleft, (constants.CHUNK_SIZE, constants.CHUNK_SIZE)
        )

        self.lights = []
        for light in data["lights"]:
            self.lights.append(
                LightData(
                    (self.world_topleft.x + light[0], self.world_topleft.y + light[1]),
                    light[2],
                    int(light[3]),
                    light[4],
                )
            )

        self.stars = data["stars"]
        self.dusts = data["dusts"]
        self.big_star = data["big_star"]
        self.tiles_mat = data["tiles"]

        self.tile_hitboxes = {}
        self.tiles_texture: Texture = None

        self.layers: dict[str, TextureRenderingLayer] = {}
        thread = threading.Thread(target=self.render_static)
        thread.start()

    def get_tile(self, tile_pos):
        return self.tiles_mat[tile_pos[1] * constants.CHUNK_SIZE + tile_pos[0]]

    def render_stars(self):
        surf_w = constants.TILE_PX * constants.CHUNK_SIZE * constants.STAR_TEX_MULT
        if constants.NEW_RENDER:
            quads = QuadsMesh()
        else:
            star_surface = pygame.Surface((surf_w, surf_w), pygame.SRCALPHA)
            star_surface.fill(0)
        for star in self.stars:
            if constants.NEW_RENDER:
                quads.add(
                    pygame.Vector2(star[0], star[1]),
                    star[2],
                    (255, 255, 255, 255 * 0.8),
                )
            else:
                sized_star = pygame.transform.scale(
                    god.assets.particle, (star[2], star[2])
                )
                star_surface.blit(
                    sized_star,
                    (
                        pygame.Vector2(star[0], star[1])
                        * constants.TILE_PX
                        * constants.STAR_TEX_MULT
                    ),
                )
        if constants.NEW_RENDER:
            self.layers["stars"] = MeshRenderingLayer(
                GeometryMesh(quads.vertices, quads.indices),
                god.assets.star_tex,
                self.world_rect,
            )
        else:
            self.layers["stars"] = TextureRenderingLayer(
                Texture.from_surface(god.windowing.renderer, star_surface),
                self.world_rect,
                None,
            )

    def render_dusts(self):
        for i, dust in enumerate(self.dusts):
            self.layers[f"dust{i}"] = TextureRenderingLayer(
                god.assets.dust_particle_tex,
                pygame.FRect(
                    self.world_rect.x + dust[0],
                    self.world_rect.y + dust[1],
                    dust[2],
                    dust[2],
                ),
                dust[3],
            )

    def render_big_star(self):
        black_hole = self.big_star[3] == -1
        dust_size = (
            BlackHole.dust_scale if black_hole else BigStar.dust_scale
        ) * self.big_star[2]
        dust_rect = (
            self.big_star[0] - (dust_size / 2) + self.world_topleft.x,
            self.big_star[1] - (dust_size / 2) + self.world_topleft.y,
            dust_size,
            dust_size,
        )
        star_rect = (
            self.big_star[0] - self.big_star[2] / 2 + self.world_topleft.x,
            self.big_star[1] - self.big_star[2] / 2 + self.world_topleft.y,
            self.big_star[2],
            self.big_star[2],
        )
        self.layers["big_star_dust"] = TextureRenderingLayer(
            (
                god.assets.dust_black_hole_particle_tex
                if black_hole
                else god.assets.dust_star_particle_tex
            ),
            dust_rect,
            BigStar.colors[0 if black_hole else self.big_star[3]],
        )
        self.layers["big_star"] = TextureRenderingLayer(
            (
                god.assets.black_hole_tex
                if black_hole
                else god.assets.big_star_texs[self.big_star[3]]
            ),
            star_rect,
            None,
        )

    def render_tiles(self):
        surf_w = constants.TILE_PX * constants.CHUNK_SIZE
        surface = pygame.Surface((surf_w, surf_w), pygame.SRCALPHA)
        at_least_one = False
        for cx in range(constants.CHUNK_SIZE):
            for cy in range(constants.CHUNK_SIZE):
                tile = self.tiles_mat[cy * constants.CHUNK_SIZE + cx]
                if tile:
                    at_least_one = True
                    tile_uid = tile[0]
                    tile_od = TileOD.get(tile_uid)
                    surface.blit(
                        god.assets.tiles[tile_od.name_id],
                        (cx * constants.TILE_PX, cy * constants.TILE_PX),
                    )
                    if tile[1]:
                        self.tile_hitboxes[(cx, cy)] = pygame.FRect(
                            self.world_topleft.x + cx, self.world_topleft.y + cy, 1, 1
                        )
                    else:
                        surface.blit(
                            god.assets.tile_not_solid_overlay,
                            (cx * constants.TILE_PX, cy * constants.TILE_PX),
                            special_flags=pygame.BLEND_RGBA_MULT,
                        )
        if at_least_one:
            self.tiles_texture = Texture.from_surface(god.windowing.renderer, surface)
            self.layers["tiles"] = TextureRenderingLayer(
                self.tiles_texture, self.world_rect, None
            )

    def render_static(self):
        if len(self.stars) > 0 and "stars" not in self.layers:
            self.render_stars()
        if len(self.dusts) > 0 and "dust0" not in self.dusts:
            self.render_dusts()
        if self.big_star is not None and "big_star" not in self.layers:
            self.render_big_star()
        self.render_tiles()

    def unload(self):
        self.loaded = False
        self.tiles_texture = None
        self.layers.clear()
