import threading

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import BigStar, BlackHole, TileOD, BuildingOD, VegetationOD
from src.client.rendering import (
    QuadsMesh,
    RenderingLayer,
    MeshRenderingLayer,
    TextureRenderingLayer,
    SpecialBuildingRenderer,
)

if constants.NEW_RENDER:
    from pygame._render import Texture, GeometryMesh
else:
    from pygame._sdl2 import Texture


class LightData:
    def __init__(self, world_pos, radius, intensity, color):
        self.world_pos = world_pos
        self.radius = radius
        self.intensity = intensity
        self.color = color


class BuildingDataHolder:
    def __init__(self, data, id_=None):
        self.data = data
        if id_ is not None:
            self.data.insert(0, id_)

    @property
    def id(self) -> str:
        return self.data[0]

    @property
    def building_od(self) -> BuildingOD:
        return BuildingOD.get(self.data[1])

    @property
    def topleft_x(self) -> int:
        return self.data[2]

    @property
    def topleft_y(self) -> int:
        return self.data[3]

    @property
    def state(self) -> str:
        return self.data[4]

    @property
    def has_energy(self) -> bool:
        return bool(self.data[5])

    @property
    def moldy(self) -> bool:
        return bool(self.data[6])

    @property
    def extra(self) -> dict | list | None:
        return self.data[7] if len(self.data) >= 8 else None


class Chunk:
    def __init__(self, data):
        self.loaded = True
        self.chunk_key = data["key"]
        self.chunk_pos = pygame.Vector2(
            [float(val) for val in self.chunk_key.split(";")]
        )
        self.world_topleft = shared.get_chunk_world_pos(self.chunk_pos)
        self.world_rect = pygame.FRect(
            self.world_topleft, (constants.CHUNK_SIZE, constants.CHUNK_SIZE)
        )
        self.static_buildings = [BuildingDataHolder(bd) for bd in data["buildings"]]
        self.special_building_renderers: list[SpecialBuildingRenderer] = []
        self.energy_conns = {}
        self.trajectory_conns = set()
        self.load_connections(data)
        self.lights = []
        self.load_lights(data)
        self.vegetation: list[tuple[VegetationOD, pygame.FRect]] = []
        self.load_vegetation(data)

        self.stars = data["stars"]
        self.dusts = data["dusts"]
        self.big_star = data["big_star"]
        self.tiles_mat = data["tiles"]

        self.tile_hitboxes = {}
        self.tiles_texture: Texture | None = None
        self.potential_debug_texture: Texture | None = None
        self.sanitizer_debug_texture: Texture | None = None
        self.vegetation_texture: Texture | None = None
        self.static_buildings_texture: Texture | None = None

        self.layers: dict[str, RenderingLayer] = {}
        thread = threading.Thread(target=self.render_static)
        thread.start()

    def load_connections(self, data):
        for a, b, energy in data["energy"]:
            self.energy_conns[frozenset({tuple(a), tuple(b)})] = energy
        for a, b in data["traj"]:
            key = (tuple(a), tuple(b))
            self.trajectory_conns.add(key)

    def load_lights(self, data):
        for light in data["lights"]:
            self.lights.append(
                LightData(
                    (self.world_topleft.x + light[0], self.world_topleft.y + light[1]),
                    light[2],
                    int(light[3]),
                    light[4],
                )
            )
        for bdata in self.static_buildings:
            state = bdata.building_od.states[bdata.state]
            if state.light is not None:
                self.lights.append(
                    LightData(
                        (
                            bdata.topleft_x + bdata.building_od.size[0] / 2,
                            bdata.topleft_y + bdata.building_od.size[1] / 2,
                        ),
                        state.light.radius,
                        state.light.intensity,
                        state.light.color,
                    )
                )

    def load_vegetation(self, data):
        for rel_x, rel_y, plant_uid in data["vegetation"]:
            plant_od = VegetationOD.get(plant_uid)
            hitbox = pygame.FRect(0, 0, plant_od.size[0], plant_od.size[1]).move_to(
                midbottom=(
                    self.world_topleft.x + rel_x + 0.5,
                    self.world_topleft.y + rel_y + 1,
                )
            )
            self.vegetation.append(
                (
                    plant_od,
                    hitbox,
                )
            )
            if plant_od.light is not None:
                self.lights.append(
                    LightData(
                        hitbox.center,
                        plant_od.light.radius,
                        plant_od.light.intensity,
                        plant_od.light.color,
                    )
                )

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
        potential_surface = None
        sanitizer_surface = None
        at_least_one = False
        for cx in range(constants.CHUNK_SIZE):
            for cy in range(constants.CHUNK_SIZE):
                tile = self.tiles_mat[cy * constants.CHUNK_SIZE + cx]
                if tile:
                    at_least_one = True
                    tile_uid = tile[0]
                    tile_od = TileOD.get(tile_uid)
                    blit_pos = (cx * constants.TILE_PX, cy * constants.TILE_PX)
                    surface.blit(
                        god.assets.tiles[tile_od.name_id],
                        blit_pos,
                    )
                    potential = potential_scaled = potential_count = sanitizers = 0
                    moldy = False
                    if len(tile) > 3 and isinstance(tile[constants.MOLD_I], list):
                        potential_count = tile[constants.MOLD_I][
                            constants.POTENTIAL_COUNT_I
                        ]
                        potential = tile[constants.MOLD_I][constants.POTENTIAL_I]
                        if potential_count != 0:
                            potential_scaled = potential / potential_count
                        else:
                            potential_scaled = potential
                        moldy = (
                            tile[constants.MOLD_I][constants.MOLDY_I] == constants.MOLDY
                        )
                        sanitizers = tile[constants.MOLD_I][constants.SANITIZERS_I]
                    if potential > 0:
                        if potential_surface is None:
                            potential_surface = pygame.Surface(
                                surface.size, pygame.SRCALPHA
                            )
                        potential_overlay = god.assets.potential_tile_overlays.get(
                            potential_count, god.assets.potential_tile_overlay_fill
                        )
                        potential_overlay.set_alpha(
                            min(
                                constants.POTENTIAL_MAX_ALPHA,
                                constants.POTENTIAL_BASE_ALPHA
                                + potential_scaled * constants.POTENTIAL_ALPHA_MULT,
                            )
                        )
                        potential_surface.blit(potential_overlay, blit_pos)
                        red_sub = min(
                            255, potential_scaled * constants.POTENTIAL_DEBUG_RED_MULT
                        )
                        potential_surface.fill(
                            (0, red_sub, 0, 0),
                            (blit_pos, (constants.TILE_PX, constants.TILE_PX)),
                            special_flags=pygame.BLEND_RGBA_SUB,
                        )
                    if sanitizers > 0:
                        if sanitizer_surface is None:
                            sanitizer_surface = pygame.Surface(
                                surface.size, pygame.SRCALPHA
                            )
                        sanitizer_surface.blit(
                            god.assets.sanitizer_tile_overlay, blit_pos
                        )
                    if moldy:
                        surface.blit(
                            god.assets.moldy_tile_overlay,
                            blit_pos,
                        )
                    if tile[1]:
                        hitbox = pygame.FRect(
                            self.world_topleft.x + cx, self.world_topleft.y + cy, 1, 1
                        )
                        self.tile_hitboxes[(cx, cy)] = hitbox
                    else:
                        surface.blit(
                            god.assets.tile_not_solid_overlay,
                            blit_pos,
                            special_flags=pygame.BLEND_RGBA_MULT,
                        )
        if at_least_one:
            self.tiles_texture = Texture.from_surface(god.windowing.renderer, surface)
            if potential_surface is not None:
                self.potential_debug_texture = Texture.from_surface(
                    god.windowing.renderer, potential_surface
                )
            if sanitizer_surface is not None:
                self.sanitizer_debug_texture = Texture.from_surface(
                    god.windowing.renderer, sanitizer_surface
                )
            self.layers["tiles"] = TextureRenderingLayer(
                self.tiles_texture, self.world_rect, None
            )

    def render_static_buildings(self):
        padding = constants.BUILDING_MAX_SIZE - 1
        surf_w = (constants.CHUNK_SIZE + padding * 2) * constants.TILE_PX
        surface = pygame.Surface((surf_w, surf_w), pygame.SRCALPHA)
        for bdata in self.static_buildings:
            image = god.assets.buildings[
                bdata.building_od.states[bdata.state].image_name
            ]
            rel_x = bdata.topleft_x - self.world_topleft.x + padding
            rel_y = bdata.topleft_y - self.world_topleft.y + padding
            surface.blit(image, (rel_x * constants.TILE_PX, rel_y * constants.TILE_PX))
            if bdata.moldy:
                mold_overlay = pygame.transform.scale(
                    god.assets.moldy_tile_overlay, image.size
                )
                surface.blit(
                    mold_overlay, (rel_x * constants.TILE_PX, rel_y * constants.TILE_PX)
                )
            if (
                bdata.extra is not None
                and bdata.building_od.name_id
                in SpecialBuildingRenderer.REGISTERED_RENDERERS
            ):
                self.special_building_renderers.append(
                    SpecialBuildingRenderer.get_renderer(bdata.building_od.name_id)(
                        bdata
                    )
                )

        self.static_buildings_texture = Texture.from_surface(
            god.windowing.renderer, surface
        )
        self.layers["static_buildings"] = TextureRenderingLayer(
            self.static_buildings_texture,
            self.world_rect.inflate(padding * 2, padding * 2),
            None,
        )

    def render_vegetation(self):
        padding = constants.VEGETATION_MAX_SIZE - 1
        surf_w = (constants.CHUNK_SIZE + padding * 2) * constants.TILE_PX
        surface = pygame.Surface((surf_w, surf_w), pygame.SRCALPHA)
        for plant_od, hitbox in self.vegetation:
            image = god.assets.vegetation[plant_od.name_id]
            rel_x = hitbox.left - self.world_topleft.x + padding
            rel_y = hitbox.top - self.world_topleft.y + padding
            surface.blit(image, (rel_x * constants.TILE_PX, rel_y * constants.TILE_PX))
        self.vegetation_texture = Texture.from_surface(god.windowing.renderer, surface)
        self.layers["vegetation"] = TextureRenderingLayer(
            self.vegetation_texture,
            self.world_rect.inflate(padding * 2, padding * 2),
            None,
        )

    def render_static(self):
        if len(self.stars) > 0 and "stars" not in self.layers:
            self.render_stars()
        if len(self.dusts) > 0 and "dust0" not in self.dusts:
            self.render_dusts()
        if self.big_star is not None and "big_star" not in self.layers:
            self.render_big_star()
        self.render_tiles()
        if len(self.static_buildings) > 0:
            self.render_static_buildings()
        if len(self.vegetation) > 0:
            self.render_vegetation()

    def unload(self):
        self.loaded = False
        self.tiles_texture = None
        self.potential_debug_texture = None
        self.sanitizer_debug_texture = None
        self.static_buildings_texture = None
        self.special_building_renderers = []
        self.vegetation_texture = None
        self.layers.clear()
