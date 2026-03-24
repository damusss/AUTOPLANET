import typing

import pygame

from src import constants
from src.client import god
from src.client.ui import ui
from src.object_data import ItemOD

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
        self.ui = ui.WorldUI(self.renderer)
        self.debug = False
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

    def render(self):
        self.render_light_overlay()
        self.render_chunks()

        players = sorted(
            list(god.world.other_players.values()) + [god.player], key=lambda p: p.pos.x
        )
        for player in players:
            self.render_player(player)
        self.render_world_ui()
        self.render_overlay_ui()
        if self.debug:
            self.render_debug()

    def render_drops(self):
        for px, py, uid, amount in god.world.drops_data:
            rect = (
                px - constants.DROP_IMAGE_SIZE / 2,
                py - constants.DROP_IMAGE_SIZE / 2,
                constants.DROP_IMAGE_SIZE,
                constants.DROP_IMAGE_SIZE,
            )
            item_name = ItemOD.get(uid).name_id
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

    def render_world_ui(self):
        if god.player.raycast is not None:
            if god.player.break_start_time is not None:
                percent = (pygame.time.get_ticks() - god.player.break_start_time) / (
                    god.player.raycast.object_data.break_time_s * 1000
                )
                frame = int(percent * len(god.assets.break_anim_texs))
                if frame >= len(god.assets.break_anim_texs):
                    frame = len(god.assets.break_anim_texs) - 1
                god.assets.break_anim_texs[frame].draw(
                    None, god.camera.rect_to_screen(god.player.raycast.hitbox)
                )

            if god.ui.can_interact_world():
                color = constants.HOVERING_TILE_COLOR
                distance = god.player.pos.distance_to(god.player.raycast.hitbox.center)
                if distance > constants.PLAYER_REACH_RADIUS or not (
                    god.player.raycast.object_data.break_requirements_id is None
                    or god.player.inventory_slots[constants.INVENTORY_HAND_I].contains(
                        ItemOD.get(
                            god.player.raycast.object_data.break_requirements_id
                        ),
                        1,
                    )
                ):
                    color = constants.HOVERING_TILE_UNAVAILABLE_COLOR
                god.assets.raycast_corner_tex.color = color
                box = god.player.raycast.hitbox
                for rect, fx, fy in (
                    ((box.x, box.y, 1, 1), False, False),
                    ((box.right - 1, box.y, 1, 1), True, False),
                    ((box.x, box.bottom - 1, 1, 1), False, True),
                    ((box.right - 1, box.bottom - 1, 1, 1), True, True),
                ):
                    god.assets.raycast_corner_tex.draw(
                        None, god.camera.rect_to_screen(rect), flip_x=fx, flip_y=fy
                    )

    def render_overlay_ui(self):
        self.ui.render()
        # ui.render_panel(self.renderer.get_viewport().inflate(-800, -400), 40, 2, outline_alpha=150)

    def render_debug(self):
        self.renderer.draw_color = constants.DEBUG_PLAYER_HITBOX_COL
        player_hitbox = god.player.hitbox
        self.renderer.draw_rect(god.camera.rect_to_screen(player_hitbox))
        self.renderer.draw_color = constants.DEBUG_TILE_HITBOX_COL
        player_hitbox = player_hitbox.inflate(0.2, 0.1)
        for chunk in god.world.loaded_chunks.values():
            if player_hitbox.colliderect(chunk.world_rect):
                for hitbox in chunk.tile_hitboxes.values():
                    self.renderer.draw_rect(god.camera.rect_to_screen(hitbox))

    def render_light_overlay(self):
        self.renderer.target = self.light_overlay_texture
        self.renderer.draw_color = 0
        self.renderer.clear()

        god.assets.white_tex.alpha = 255
        god.assets.white_tex.color = constants.AMBIENT_COLOR
        god.assets.white_tex.draw(None, self.renderer.get_viewport())
        for light in god.world.visible_lights:
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

    def render_chunks(self):
        for chunk in god.world.loaded_chunks.values():
            for name, layer in chunk.layers.items():
                if name == "tiles":
                    continue
                layer.render(self.renderer)

        self.renderer.target = self.lit_texture_layer
        self.renderer.draw_color = 0
        self.renderer.clear()

        for chunk in god.world.loaded_chunks.values():
            if "tiles" in chunk.layers:
                chunk.layers["tiles"].render(self.renderer)
        self.render_drops()

        self.light_overlay_texture.draw(None, self.lit_texture_layer.get_rect())

        self.renderer.target = None
        self.lit_texture_layer.draw(None, self.renderer.get_viewport())
