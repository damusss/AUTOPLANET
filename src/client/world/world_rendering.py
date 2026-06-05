import math
import typing
import random

import pygame

from src import shared
from src import constants
from src.client import god
from src.client.rendering import RenderingLayer, SpecialBuildingRenderer
from src.client.ui import screen_ui, camera_ui
from src.client.world import special_renderers
from src.object_data import ItemOD, BuildingOD
from src.client.world.chunk import LightData

if constants.NEW_RENDER:
    from pygame._render import Texture
else:
    from pygame._sdl2 import Texture

if typing.TYPE_CHECKING:
    from src.client.world.player import PlayerLike


class WorldRendering:
    def __init__(self):
        god.rendering = self
        self.renderer = god.windowing.renderer
        self.ui = screen_ui.ScreenUI(self.renderer)
        self.camera_ui = camera_ui.CameraUI(self.renderer)
        self.debug = False
        self.energy_debug = False
        self.computer_debug = False
        self.trajectory_debug = False
        self.edit_trajectory_hover_available = constants.BUILDING_STATUS_AVAILABLE
        self.edit_trajectory_too_far_units = None
        assert special_renderers
        self.refresh_light_textures()
        if constants.NEW_RENDER and False:
            self.star_intermediate_texture = Texture(
                self.renderer,
                (constants.TILE_PX * constants.CHUNK_SIZE * constants.STAR_TEX_MULT,)
                * 2,
                target=True,
            )
            self.star_intermediate_texture.blend_mode = pygame.BLENDMODE_BLEND

    def refresh_light_textures(self):
        self.lit_texture_layer = Texture(
            self.renderer, god.windowing.window.size, target=True
        )
        self.lit_texture_layer.blend_mode = pygame.BLENDMODE_BLEND
        self.light_overlay_texture = Texture(
            self.renderer, god.windowing.window.size, target=True
        )
        self.light_overlay_texture.blend_mode = pygame.BLENDMODE_MUL
        self.energy_debug_overlay_texture = Texture(
            self.renderer, god.windowing.window.size, target=True
        )
        self.energy_debug_overlay_texture.blend_mode = pygame.BLENDMODE_BLEND
        self.energy_debug_overlay_texture.alpha = constants.ENERGY_DEBUG_ALPHA
        self.ui.refresh_screen_textures()

    def render(self):
        self.render_light_overlay()
        self.render_chunks()

        players = sorted(
            list(god.world.other_players.values()) + [god.player], key=lambda p: p.pos.x
        )
        self.camera_ui.render_below()
        for player in players:
            self.render_player(player)
        self.camera_ui.render_above()
        self.ui.render()
        self.edit_trajectory_hover_available = constants.BUILDING_STATUS_AVAILABLE
        self.edit_trajectory_too_far_units = None
        if self.debug:
            self.render_debug()

    def render_drops(self):
        for px, py, uid, anim_offset in god.world.drops_data:
            item_name = ItemOD.get(uid).name_id
            size = constants.DROP_SIZE + (
                (
                    constants.DROP_SIZE
                    * god.assets.drop_inflate_percentages.get(item_name, 0)
                    - constants.DROP_SIZE
                )
                / 2
            )
            animation = shared.get_float_anim(
                constants.DROP_ANIM_H, constants.DROP_ANIM_TIME_MULT, anim_offset
            )
            rect = (
                px - size / 2,
                py - size / 2 - animation,
                size,
                size,
            )
            god.assets.item_texs[item_name].draw(None, god.camera.rect_to_screen(rect))

    def render_player(self, player: PlayerLike):
        player.texture.draw(
            None,
            god.camera.rect_to_screen(
                (
                    player.pos
                    - pygame.Vector2(constants.PLAYER_SIZE, constants.PLAYER_SIZE) / 2,
                    (constants.PLAYER_SIZE,) * 2,
                )
            ),
            flip_x=player.vel.x < 0,
        )
        if len(god.world.other_players) > 0:
            col = pygame.Color(
                constants.PLAYER_NAME_UI_COLOR
                if player == god.player
                else constants.OTHER_PLAYER_NAME_UI_COLOR
            )
            if god.camera.zoom >= 1.5:
                self.render_player_name(player, col)
            else:
                self.render_player_indicator(player, col)

    def render_player_name(self, player: PlayerLike, col):
        col.a = constants.PLAYER_NAME_UI_ALPHA
        name = player.name if player != god.player else god.client.name
        name_tex = god.assets.font.get_texture(name)
        midbottom = pygame.Vector2(player.pos.x, player.pos.y - 0.5 - 0.08)
        name_rect = pygame.FRect(
            0,
            0,
            constants.PLAYER_NAME_UI_HEIGHT * (name_tex.width / name_tex.height),
            constants.PLAYER_NAME_UI_HEIGHT,
        ).move_to(midbottom=midbottom)

        self.renderer.draw_color = col
        self.renderer.fill_rect(god.camera.rect_to_screen(name_rect.inflate(0.05, 0)))
        name_tex.draw(None, god.camera.rect_to_screen(name_rect))

    def render_player_indicator(self, player: PlayerLike, col):
        col.a = int(constants.PLAYER_NAME_UI_ALPHA * 1.5)
        bottom_point = player.pos + pygame.Vector2(0, -0.6)
        height = constants.PLAYER_NAME_UI_HEIGHT
        topleft_point = pygame.Vector2(
            bottom_point.x - height / 2, bottom_point.y - height * 0.8
        )
        topright_point = pygame.Vector2(
            bottom_point.x + height / 2, bottom_point.y - height * 0.8
        )
        self.renderer.draw_color = col
        self.renderer.fill_triangle(
            god.camera.to_screen(bottom_point),
            god.camera.to_screen(topleft_point),
            god.camera.to_screen(topright_point),
        )

    def render_debug(self):
        self.renderer.draw_color = constants.DEBUG_PLAYER_HITBOX_COL
        player_hitbox = god.player.hitbox
        self.renderer.draw_rect(god.camera.rect_to_screen(player_hitbox))
        player_hitbox = player_hitbox.inflate(0.2, 0.1)
        self.renderer.draw_color = constants.DEBUG_TILE_HITBOX_COL
        for chunk in god.world.loaded_chunks.values():
            if player_hitbox.colliderect(chunk.world_rect):
                for hitbox in chunk.tile_hitboxes.values():
                    self.renderer.draw_rect(god.camera.rect_to_screen(hitbox))
                for bd in chunk.static_buildings:
                    if bd.building_od.floor:
                        self.renderer.draw_rect(
                            god.camera.rect_to_screen(
                                pygame.FRect(
                                    (bd.topleft_x, bd.topleft_y), bd.building_od.size
                                )
                            )
                        )
                self.renderer.draw_color = constants.DEBUG_CHUNK_BORDER_COLOR
                self.renderer.draw_rect(god.camera.rect_to_screen(chunk.world_rect))
                self.renderer.draw_color = constants.DEBUG_TILE_HITBOX_COL
        for px, py, uid, amount in god.world.drops_data:
            rect = (
                px - constants.DROP_SIZE / 2,
                py - constants.DROP_SIZE / 2,
                constants.DROP_SIZE,
                constants.DROP_SIZE,
            )
            self.renderer.draw_color = "magenta"
            self.renderer.draw_rect(god.camera.rect_to_screen(rect))

    def render_light_overlay(self):
        self.renderer.target = self.light_overlay_texture
        self.renderer.draw_color = 0
        self.renderer.clear()

        god.assets.white_tex.alpha = constants.OPAQUE
        god.assets.white_tex.color = constants.AMBIENT_COLOR
        god.assets.white_tex.draw(None, god.windowing.viewport)

        moving_lights = []
        for data in god.world.moving_buildings_data.values():
            od = BuildingOD.get(data[0])
            light = od.states["default"].light
            if light is not None:
                moving_lights.append(
                    LightData(
                        (data[1], data[2]), light.radius, light.intensity, light.color
                    )
                )
        for light in god.world.visible_lights + moving_lights:
            god.assets.light_tex.alpha = light.intensity
            god.assets.light_tex.color = light.color
            pos = light.world_pos
            if light.world_pos == "player":
                pos = god.player.pos
            elif isinstance(pos, str) and pos.startswith("other_player_"):
                player_id = int(pos.split("_")[-1])
                if player_id in god.world.other_players:
                    pos = god.world.other_players[player_id].pos
                else:
                    continue
            god.assets.light_tex.draw(
                None,
                god.camera.rect_to_screen(
                    (
                        pos - pygame.Vector2(light.radius, light.radius),
                        (light.radius * 2,) * 2,
                    )
                ),
            )

        self.renderer.target = None

    def render_moving_building(self, id_, uid, cx, cy, dx, display_data):
        od = BuildingOD.get(uid)
        size = (
            od.size[0] * od.hitbox_multiplier,
            od.size[1] * od.hitbox_multiplier,
        )
        if id_ not in god.world.bots_anim_offset:
            god.world.bots_anim_offset[id_] = random.uniform(0, math.tau)
        anim_offset = god.world.bots_anim_offset[id_]
        animation = shared.get_float_anim(
            constants.BOT_ANIM_H, constants.BOT_ANIM_TIME_MULT, anim_offset
        )
        rect = pygame.FRect(0, 0, size[0], size[1]).move_to(center=(cx, cy - animation))
        image_tex = god.assets.item_texs[od.name_id]
        image_tex.draw(None, god.camera.rect_to_screen(rect), flip_x=dx > 0)
        if display_data is not None:
            display_od = ItemOD.get(display_data)
            image_tex = god.assets.item_texs[display_od.name_id]
            item_size = size[0] / 2
            offset = size[0] / 6
            rect = god.camera.rect_to_screen(
                pygame.FRect(0, 0, item_size, item_size)
                .move_to(
                    topleft=(
                        rect.centerx + offset * dx - (rect.w / 2 * (dx < 0)),
                        rect.centery + offset,
                    )
                )
                .inflate(item_size / 2, item_size / 2)
            )
            image_tex.color = "black"
            image_tex.draw(
                None,
                rect.inflate(
                    rect.w / constants.TILE_PX * 2, rect.h / constants.TILE_PX * 2
                ),
            )
            image_tex.color = "white"
            image_tex.draw(
                None,
                rect,
            )

    def render_chunks(self):
        for chunk in god.world.loaded_chunks.values():
            for name, layer in chunk.layers.items():
                if name in ["tiles", "static_buildings"]:
                    continue
                layer.render(self.renderer)

        self.renderer.target = self.lit_texture_layer
        self.renderer.draw_color = 0
        self.renderer.clear()

        vegetation_layers: list[RenderingLayer] = []
        building_layers: list[tuple[RenderingLayer, list[SpecialBuildingRenderer]]] = []
        for chunk in god.world.loaded_chunks.values():
            if "tiles" in chunk.layers:
                chunk.layers["tiles"].render(self.renderer)
            if "vegetation" in chunk.layers:
                vegetation_layers.append(chunk.layers["vegetation"])
            if "static_buildings" in chunk.layers:
                building_layers.append(
                    (chunk.layers["static_buildings"], chunk.special_building_renderers)
                )
        for layer in vegetation_layers:
            layer.render(self.renderer)
        for layer, special_building_renderers in building_layers:
            layer.render(self.renderer)
            for special_renderer in special_building_renderers:
                special_renderer.render(self.renderer)
        self.render_drops()
        for id_, data in god.world.moving_buildings_data.items():
            self.render_moving_building(
                id_, data[0], data[1], data[2], data[3], data[5]
            )

        self.light_overlay_texture.draw(None, self.lit_texture_layer.get_rect())

        self.renderer.target = None
        self.lit_texture_layer.draw(None, god.windowing.viewport)
