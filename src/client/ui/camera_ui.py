import math

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import BuildingOD
from src.client.ui.panel import render_panel_bg

if constants.NEW_RENDER:
    from pygame._render import Renderer
else:
    from pygame._sdl2 import Renderer


class CameraUI:
    def __init__(self, renderer):
        self.renderer: Renderer = renderer

    def render_below(self):
        if (
            god.player.raycast is not None
            and god.player.building_preview is None
            and god.ui.can_interact_world()
            and god.player.break_start_time is not None
        ):
            self.render_break_anim(
                god.player.break_start_time,
                god.player.raycast.hitbox.center,
                god.player.raycast.object_data.break_time_s * god.player.break_mult,
                [god.player.raycast.object_data.uid, god.player.raycast.data[0]]
                if god.player.raycast.type == constants.RAYCAST_BUILDING
                else None,
            )
        for other_player in god.world.other_players.values():
            if other_player.break_data is not None:
                self.render_break_anim(*other_player.break_data)
        self.render_building_warnings()
        if god.rendering.energy_debug:
            self.render_energy_debug()

    def render_break_anim(self, start_time, center, break_time_s, building_data):
        percent = (pygame.time.get_ticks() - start_time) / (break_time_s * 1000)
        frame = int(percent * len(god.assets.break_anim_texs))
        if frame >= len(god.assets.break_anim_texs):
            frame = len(god.assets.break_anim_texs) - 1
        image = god.assets.break_anim_texs[frame]
        image.color = "black"
        size = 1
        anim = 0
        if building_data is not None:
            image.color = (30, 30, 30, 255)
            object_data = BuildingOD.get(building_data[0])
            size *= object_data.hitbox_multiplier
            if building_data[1] in god.world.bots_anim_offset:
                anim = shared.get_float_anim(
                    constants.BOT_ANIM_H,
                    constants.BOT_ANIM_TIME_MULT,
                    god.world.bots_anim_offset[building_data[1]],
                )
        image.draw(
            None,
            god.camera.rect_to_screen(
                pygame.FRect(0, 0, size, size).move_to(
                    center=(
                        center[0],
                        center[1] - anim,
                    )
                )
            ),
        )

    def render_building_warnings(self):
        for bd in god.world.no_energy_buildings:
            rect = pygame.FRect(
                bd.topleft_x,
                bd.topleft_y,
                bd.building_od.size[0],
                bd.building_od.size[1],
            )
            icon_size = 0.5
            left_rect = pygame.FRect(0, 0, icon_size, icon_size).move_to(
                topright=(rect.center)
            )
            right_rect = pygame.FRect(0, 0, icon_size, icon_size).move_to(
                topleft=rect.center
            )
            warn_icon = god.assets.icons_texs["warning"]
            warn_icon.color = constants.RED_BAD
            plug_icon = god.assets.icons_texs["plug"]
            plug_icon.color = constants.RED_BAD
            panel = god.camera.rect_to_screen(left_rect.move_to(width=left_rect.w * 2))
            render_panel_bg(panel, panel.h * constants.UI_SLOT_CORNER_SIZE_MULT)
            warn_icon.draw(None, god.camera.rect_to_screen(left_rect))
            plug_icon.draw(None, god.camera.rect_to_screen(right_rect))

    def render_energy_debug(self):
        self.renderer.target = god.rendering.energy_debug_overlay_texture
        self.renderer.draw_color = 0
        self.renderer.clear()
        with_energy_data = []
        conns = {}
        for chunk in god.world.loaded_chunks.values():
            for bd in chunk.static_buildings:
                tex = None
                if bd.building_od == BuildingOD.objects.energy_plant:
                    tex = god.assets.energy_plant_debug_tex
                elif bd.building_od == BuildingOD.objects.energy_transmitter:
                    tex = god.assets.energy_transmitter_debug_tex

                if tex is not None:
                    rect = god.camera.rect_to_screen(
                        pygame.FRect(
                            (0, 0), (bd.building_od.energy_radius * 2,) * 2
                        ).move_to(
                            center=(
                                bd.topleft_x + bd.building_od.size[0] / 2,
                                bd.topleft_y + bd.building_od.size[1] / 2,
                            )
                        )
                    )
                    if not bd.has_energy:
                        tex.color = constants.NO_ENERGY_DEBUG_COLOR
                        tex.draw(
                            None,
                            rect,
                        )
                    else:
                        with_energy_data.append((tex, rect))
            if len(chunk.energy_conns) > 0:
                conns.update(chunk.energy_conns)
        for tex, rect in with_energy_data:
            tex.color = constants.ENERGY_DEBUG_COLOR
            tex.draw(None, rect)
        self.renderer.target = None
        god.rendering.energy_debug_overlay_texture.draw(
            None, self.renderer.get_viewport()
        )
        for (a, b), has_energy in conns.items():
            self.renderer.draw_color = (
                constants.ENERGY_DEBUG_COLOR
                if has_energy
                else constants.NO_ENERGY_DEBUG_COLOR
            )
            self.renderer.draw_line(god.camera.to_screen(a), god.camera.to_screen(b))

    def render_above(self):
        if god.ui.can_interact_world():
            if (
                god.player.raycast is not None
                and god.player.raycast.type != constants.RAYCAST_DROP
                and god.player.building_preview is None
            ):
                if (
                    god.player.edit_trajectory_bot is None
                    or god.player.raycast.type != constants.RAYCAST_BUILDING
                    or god.player.raycast.data[0] == god.player.edit_trajectory_bot
                ):
                    self.render_raycast()
            if god.player.edit_trajectory_bot is not None:
                self.render_edit_trajectory()
        if god.rendering.trajectory_debug:
            self.render_trajectory_debug()
        if god.player.building_preview is not None:
            self.render_building_preview(
                god.input.mouse_world,
                god.player.building_preview,
                god.player.building_available,
            )
        for other_player in god.world.other_players.values():
            if other_player.building_preview is not None:
                preview = other_player.building_preview
                self.render_building_preview(
                    preview[0], BuildingOD.get(preview[1]), preview[2], other_player.pos
                )

    def render_trajectory_debug(self):
        for chunk in god.world.loaded_chunks.values():
            for a, b in chunk.trajectory_conns:
                self.render_trajectory_line(a, b)

    def render_raycast(self):
        color = constants.HOVERING_TILE_COLOR
        distance = god.player.pos.distance_to(god.player.raycast.hitbox.center)
        if distance > (constants.PLAYER_REACH_RADIUS) or not (
            god.player.raycast.object_data.break_requirements is None
            or god.player.inventory_slots[constants.INVENTORY_HAND_I].contains_any(
                god.player.raycast.object_data.break_requirements,
                1,
            )
        ):
            if (
                god.player.raycast.type == constants.RAYCAST_BUILDING
                and distance <= constants.PLAYER_INTERACT_RADIUS
                and god.player.raycast.object_data.interface
            ):
                color = constants.HOVERING_TILE_FAR_COLOR
            else:
                color = constants.HOVERING_TILE_UNAVAILABLE_COLOR

        box = god.player.raycast.hitbox
        m = 1
        if god.player.raycast.type == constants.RAYCAST_BUILDING:
            m *= god.player.raycast.object_data.hitbox_multiplier
            if god.player.raycast.data[0] in god.world.bots_anim_offset:
                anim = shared.get_float_anim(
                    constants.BOT_ANIM_H,
                    constants.BOT_ANIM_TIME_MULT,
                    god.world.bots_anim_offset[god.player.raycast.data[0]],
                )
                box = box.move(0, -anim)
        self.render_hover_hitbox(box, m, color)

    def render_hover_hitbox(self, box: pygame.FRect, m, color):
        god.assets.raycast_corner_tex.color = color
        for rect, fx, fy in (
            ((box.x, box.y, m, m), False, False),
            ((box.right - m, box.y, m, m), True, False),
            ((box.x, box.bottom - m, m, m), False, True),
            ((box.right - m, box.bottom - m, m, m), True, True),
        ):
            god.assets.raycast_corner_tex.draw(
                None, god.camera.rect_to_screen(rect), flip_x=fx, flip_y=fy
            )

    def render_edit_trajectory(self):
        if god.player.edit_trajectory_bot not in god.world.moving_buildings_data:
            return
        available = god.player.edit_trajectory_validate_hover()
        if available is not None:
            god.rendering.edit_trajectory_hover_available = available
            other_anim = 0
            if god.player.raycast.data[0] in god.world.bots_anim_offset:
                other_anim = shared.get_float_anim(
                    constants.BOT_ANIM_H,
                    constants.BOT_ANIM_TIME_MULT,
                    god.world.bots_anim_offset[god.player.raycast.data[0]],
                )
            self.render_building_preview(
                (
                    god.player.raycast.hitbox.centerx,
                    god.player.raycast.hitbox.centery - other_anim,
                ),
                god.player.raycast.object_data,
                available,
                energy_debug=False,
            )
        data = god.world.moving_buildings_data[god.player.edit_trajectory_bot]
        anim = 0
        if god.player.edit_trajectory_bot in god.world.bots_anim_offset:
            anim = shared.get_float_anim(
                constants.BOT_ANIM_H,
                constants.BOT_ANIM_TIME_MULT,
                god.world.bots_anim_offset[god.player.edit_trajectory_bot],
            )
        box = pygame.FRect(0, 0, 1, 1).move_to(center=(data[1], data[2] - anim))
        self.render_hover_hitbox(box, 1, constants.TRAJECTORY_COLOR)
        traj = data[4]
        points = []
        for name in ["in", "out"]:
            if traj[name]:
                box = pygame.FRect(traj[name][1]).inflate(0.2, 0.2)
                points.append(box.center)
                tex = god.assets.icons_texs["in" if name == "out" else "out"]
                tex.color = constants.TRAJECTORY_COLOR
                tex.draw(None, god.camera.rect_to_screen(box))
        if len(points) == 2:
            dist = pygame.Vector2(points[0]).distance_to(points[1])
            god.rendering.edit_trajectory_too_far_units = None
            if dist > constants.BOT_TRAJECTORY_MAX_SIZE:
                god.rendering.edit_trajectory_too_far_units = round(
                    dist - constants.BOT_TRAJECTORY_MAX_SIZE, 1
                )
            if not god.rendering.trajectory_debug:
                self.render_trajectory_line(*points)

    def render_trajectory_line(self, a, b):
        color = constants.TRAJECTORY_COLOR
        a, b = pygame.Vector2(a), pygame.Vector2(b)
        if a.distance_to(b) > constants.BOT_TRAJECTORY_MAX_SIZE:
            color = constants.TRAJECTORY_ERROR_COLOR
        self.renderer.draw_color = color
        self.renderer.draw_line(god.camera.to_screen(a), god.camera.to_screen(b))
        caret = god.assets.icons_texs["right-caret"]
        caret.color = color
        diff = b - a
        angle = math.degrees(math.atan2(diff.x, diff.y))
        caret.draw(
            None,
            god.camera.rect_to_screen(
                pygame.FRect(
                    0,
                    0,
                    constants.TRAJECTORY_ARROW_SIZE,
                    constants.TRAJECTORY_ARROW_SIZE,
                ).move_to(center=a + diff / 2)
            ),
            -angle + 90,
        )

    def render_building_preview(
        self, center, preview: BuildingOD, available, player_pos=None, energy_debug=True
    ):
        size = preview.size
        if preview.static:
            topleft = shared.get_building_topleft(center, preview.size)
        else:
            size = (
                (preview.size[0] * preview.hitbox_multiplier),
                (preview.size[1] * preview.hitbox_multiplier),
            )
            topleft = pygame.Vector2(
                center[0] - size[0] / 2,
                center[1] - size[1] / 2,
            )
        rect = pygame.FRect(topleft, size)
        color = color = (
            constants.GREEN_GOOD
            if available == constants.BUILDING_STATUS_AVAILABLE
            else constants.RED_BAD
        )
        if player_pos is not None:
            pgcol = pygame.Color(color)
            pgcol.a = constants.BUILDING_PREVIEW_ALPHA
            self.renderer.draw_color = pgcol
            self.renderer.draw_line(
                god.camera.to_screen(player_pos), god.camera.to_screen(rect.center)
            )
        if energy_debug and preview.energy_endpoint_type != constants.ENDPOINT_MACHINE:
            debug_tex = (
                god.assets.energy_plant_debug_tex
                if preview == BuildingOD.objects.energy_plant
                else god.assets.energy_transmitter_debug_tex
            )
            debug_tex.color = constants.ENERGY_DEBUG_COLOR
            debug_tex.alpha = constants.ENERGY_DEBUG_ALPHA
            debug_tex.draw(
                None,
                god.camera.rect_to_screen(
                    pygame.FRect((0, 0), (preview.energy_radius * 2,) * 2).move_to(
                        center=rect.center
                    )
                ),
            )
            debug_tex.alpha = constants.OPAQUE
        tex = god.assets.building_preview_texs[preview.name_id]
        tex.color = color
        tex.alpha = constants.BUILDING_PREVIEW_ALPHA
        tex.draw(None, god.camera.rect_to_screen(rect))
