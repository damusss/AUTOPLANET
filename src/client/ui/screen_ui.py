import typing

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD, BuildingOD
from src.client.ui import buildings
from src.client.ui.panel import render_panel_bg, render_panel_outline
from src.client.ui.raycast_info import RaycastInfoUI
from src.client.ui.inventory import FloatingSlot
from src.client.world.chunk import BuildingDataHolder
from src.client.ui.crafting import CraftingInterface
from src.client.ui.building import BuildingInterface
from src.client.ui.research import ResearchInterface
from src.client.ui.inventory import InventoryInterface

if constants.NEW_RENDER:
    from pygame._render import Texture
else:
    from pygame._sdl2 import Texture


class UIRaycastHit:
    def __init__(
        self,
        item,
        crafting=False,
        amount=0,
        type_=constants.RAYCAST_UI_ITEM,
        filter_=None,
    ):
        self.type = type_
        self.item: ItemOD = item
        self.crafting = crafting
        self.amount = amount
        self.filter = filter_
        self.object_data = self.item


class ScreenUI:
    def __init__(self, renderer):
        god.ui = self
        self.ui_raycast = None
        self.inventory_open = False
        self.open_interface = None
        self.research_open = False
        self.renderer = renderer
        self.b = 0
        self.raycast_info = RaycastInfoUI()
        self.inventory = InventoryInterface()
        self.research = ResearchInterface()
        self.crafting_interface = CraftingInterface()
        self.cursor = constants.CURSOR_IDLE_WORLD
        self.hotbar_rect = pygame.Rect()
        self.overlay_menu_func: (
            typing.Callable[[pygame.Rect], shared.Slot | None] | None
        ) = None
        self.building_interfaces: dict[BuildingOD, BuildingInterface] = (
            BuildingInterface.get_interfaces()
        )
        assert buildings

    @property
    def any_menu_open(self):
        return self.inventory_open or self.research_open

    def refresh_screen_textures(self):
        pause_surf = pygame.Surface(god.windowing.size, pygame.SRCALPHA)
        y = 0
        while y < pause_surf.height:
            pygame.draw.line(
                pause_surf,
                constants.UI_PAUSE_OVERLAY_COL,
                (0, y),
                (pause_surf.width, y),
                constants.UI_PAUSE_OVERLAY_LINE_HEIGHT,
            )
            y += constants.UI_PAUSE_OVERLAY_LINE_HEIGHT * 2
        self.pause_overlay_tex = Texture.from_surface(self.renderer, pause_surf)
        self.pause_overlay_tex.alpha = constants.UI_PAUSE_OVERLAY_ALPHA

    def mouse_clicked(self, event: pygame.Event):
        interface_slots = []
        overlay_menu_func = self.overlay_menu_func
        if self.open_interface:
            self.open_interface.mouse_clicked(event)
            interface_slots = self.open_interface.get_slots()
        if overlay_menu_func is not None:
            return
        self.inventory.mouse_clicked(event, interface_slots)

    def mouse_clicked_outside_inventory(self, event: pygame.Event):
        for i, slot in enumerate(god.player.hotbar):
            if slot.item is None or slot.amount <= 0:
                continue
            if slot.hitbox.collidepoint(event.pos):
                self.click_hotbar(i)
                break

    def click_hotbar(self, i):
        slot = god.player.hotbar[i]
        if slot.item is None or slot.amount <= 0:
            return
        god.player.set_building_preview(slot.item.building)
        if god.player.building_preview is None:
            slot_to_concentrate = None
            for inv_slot in god.player.inventory_slots:
                if not inv_slot.empty and inv_slot.item == slot.item:
                    slot_to_concentrate = inv_slot
                    break
            if slot_to_concentrate is not None:
                self.inventory.floating_slot = FloatingSlot(
                    slot_to_concentrate, slot_to_concentrate.amount
                )
                god.client.conn.mail(
                    constants.MAIL_INVENTORY_ACTION,
                    action=constants.INVENTORY_ACTION_CONCENTRATE,
                    source={"cont": slot_to_concentrate.cont, "slot": None},
                    dest={
                        "cont": slot_to_concentrate.cont,
                        "slot": slot_to_concentrate.i,
                    },
                    amount=None,
                )
        else:
            self.inventory.floating_slot = FloatingSlot(None, 0)

    def can_interact_world(self):
        hovering_hotbar = self.hotbar_rect.collidepoint(god.user_input.mouse_screen)
        if self.any_menu_open:
            return self.ui_raycast is None
        return not hovering_hotbar

    def drop_floating_slot(self, whole_stack=False):
        if self.inventory.floating_slot.source_slot is None:
            return
        god.client.conn.mail(
            constants.MAIL_INVENTORY_ACTION,
            action=constants.INVENTORY_ACTION_DROP,
            source={
                "cont": self.inventory.floating_slot.source_slot.cont,
                "slot": self.inventory.floating_slot.source_slot.i,
            },
            dest={
                "cont": "right"
                if god.user_input.mouse_world.x >= god.player.pos.x
                else "left",
                "slot": None,
            },
            amount=self.inventory.floating_slot.amount if whole_stack else 1,
        )

    def close_any_menu(self):
        if self.inventory_open:
            self.toggle_inventory()
        if self.research_open:
            self.toggle_research()

    def toggle_research(self):
        if not self.research_open:
            self.close_any_menu()
            god.player.set_building_preview(None)
            god.player.set_edit_trajectory(None)
            self.research.subscribe()
        else:
            self.research.unsubscribe()
            self.research.reset_camera()
        self.research_open = not self.research_open

    def toggle_inventory(self, manual=False):
        if not self.inventory_open:
            self.close_any_menu()
            self.open_interface = self.crafting_interface
            god.player.set_building_preview(None)
            god.player.set_edit_trajectory(None)
        else:
            if manual:
                building = None
                if self.inventory.floating_slot.source_slot is not None:
                    if self.inventory.floating_slot.item is not None:
                        building = self.inventory.floating_slot.item.building
                if building is not None:
                    god.player.set_building_preview(building)
                    self.inventory.floating_slot = FloatingSlot(None, 0)
            else:
                self.inventory.floating_slot = FloatingSlot(None, 0)
            self.open_interface.unsubscribe()
            self.open_interface.on_exit()
            self.open_interface = None
            self.overlay_menu_func = None
        self.inventory_open = not self.inventory_open

    def refresh_building_interact(self, base_data, building_data):
        data_holder = BuildingDataHolder(
            base_data, building_data.get("building_id", None)
        )
        if not self.inventory_open:
            self.toggle_inventory()
        old_interface = self.open_interface
        self.open_interface = self.building_interfaces[data_holder.building_od]
        if old_interface != self.open_interface and old_interface:
            old_interface.on_exit()
        if old_interface != self.open_interface and isinstance(
            old_interface, BuildingInterface
        ):
            self.open_interface.unsubscribe()
            self.open_interface = self.building_interfaces[data_holder.building_od]
        if (
            self.open_interface.building_data is not None
            and self.open_interface.building_data.id != data_holder.id
        ):
            self.open_interface.unsubscribe()
        self.open_interface.refresh_data(data_holder, building_data)
        self.open_interface.on_enter()

    def render_stats(self):
        box_w = god.windowing.width * constants.UI_BARS_W_MULT
        bar_w = box_w - self.b * 2
        bar_h = bar_w * constants.UI_BARS_H_MULT
        cs = bar_h / 2
        box_h = bar_h * 2 + self.b * 3
        box = pygame.Rect((self.b, self.b, box_w, box_h))
        render_panel_bg(box, cs)
        render_panel_bg(
            (
                box.x + self.b,
                box.y + self.b,
                bar_w * (god.player.health / constants.PLAYER_MAX_HEALTH),
                bar_h,
            ),
            cs,
            bg_alpha=constants.OPAQUE,
            bg_color=constants.UI_HEALTH_COL,
        )
        render_panel_bg(
            (
                box.x + self.b,
                box.y + self.b * 2 + bar_h,
                bar_w * (god.player.energy / constants.PLAYER_MAX_ENERGY),
                bar_h,
            ),
            cs,
            bg_alpha=constants.OPAQUE,
            bg_color=constants.UI_ENERGY_COL,
        )
        render_panel_outline(
            (box.x + self.b, box.y + self.b, bar_w, bar_h),
            cs,
            outline_alpha=constants.OPAQUE,
            outline_color=constants.UI_BARS_OUTLINE_COL,
        )
        render_panel_outline(
            (box.x + self.b, box.y + self.b * 2 + bar_h, bar_w, bar_h),
            cs,
            outline_alpha=constants.OPAQUE,
            outline_color=constants.UI_BARS_OUTLINE_COL,
        )
        circle = pygame.Rect(box.x + self.b, box.y + self.b, bar_h, bar_h)
        render_panel_bg(
            circle.inflate(2, 2), cs, constants.OPAQUE, constants.UI_BARS_OUTLINE_COL
        )
        god.assets.health_tex.draw(None, circle.inflate(-4, -4))
        circle = pygame.Rect(
            box.x + self.b, box.y + self.b * 2 + bar_h, bar_h, bar_h
        ).inflate(2, 2)
        render_panel_bg(
            circle.inflate(2, 2), cs, constants.OPAQUE, constants.UI_BARS_OUTLINE_COL
        )
        god.assets.energy_tex.draw(None, circle.inflate(-4, -4))

        pos_tex, pos_rect = god.assets.font.get_texture_and_rect(
            f"X: {int(god.player.pos.x)} Y: {-int(god.player.pos.y)}",
            constants.UI_INFO_DESCR_COL,
            bar_h,
        )
        pos_rect = pos_rect.move_to(topleft=(self.b * 2, box.bottom + self.b))
        pos_tex.draw(None, pos_rect)
        fps_tex, fps_rect = god.assets.font.get_texture_and_rect(
            f"FPS: {round(god.world.fps)}", constants.UI_INFO_DESCR_COL, bar_h
        )
        fps_rect = fps_rect.move_to(topleft=(self.b * 2, pos_rect.bottom + self.b))
        fps_tex.draw(None, fps_rect)
        return box.right + self.b

    def render_debug_indicators(self, left):
        size = god.windowing.height * constants.UI_DEBUG_INDICATORS_H_MULT
        for item_name, active, key_num, color, alpha_boost in (
            (
                "energy_transmitter",
                god.rendering.energy_debug,
                1,
                constants.ENERGY_DEBUG_COLOR,
                0,
            ),
            ("bot", god.rendering.trajectory_debug, 2, constants.TRAJECTORY_COLOR, 0),
            (
                "laboratory",
                god.rendering.computer_debug,
                3,
                constants.UI_COMPUTER_DEBUG_INDICATOR_COLOR,
                35,
            ),
        ):
            tex = god.assets.building_preview_texs[item_name]
            tex.alpha = (
                constants.OPAQUE_INDICATOR_ALPHA
                if active
                else constants.GHOST_INDICATOR_ALPHA
            ) + alpha_boost
            tex.color = color
            rect = pygame.Rect(0, 0, size, size).move_to(topleft=(left, self.b))
            tex.draw(None, rect)
            tex.alpha = constants.OPAQUE
            tex.color = "white"
            god.assets.font.font.outline = 1
            key_tex_o, key_rect_o = god.assets.font.get_texture_and_rect(
                f"F{key_num}", "black", size / 1.3
            )
            god.assets.font.font.outline = 0
            key_tex, key_rect = god.assets.font.get_texture_and_rect(
                f"F{key_num}", "white", size / 1.3
            )
            key_tex_o.draw(None, key_rect_o.move_to(center=rect.center))
            key_tex.draw(None, key_rect.move_to(center=rect.center))
            left += size + self.b

    def render_drag_enabled(self):
        text_h = god.windowing.width * constants.UI_DRAG_ENABLED_TEXT_H
        drag_tex, drag_rect = god.assets.font.get_texture_and_rect(
            "Drag enabled", constants.UI_INFO_DESCR_COL, text_h
        )
        drag_rect = drag_rect.move_to(
            midbottom=(
                god.user_input.mouse_screen.x,
                god.user_input.mouse_screen.y - constants.UI_CURSOR_OFFSET * 2,
            )
        )
        god.assets.font.font.outline = 1
        drag_tex_outline, drag_rect_outline = god.assets.font.get_texture_and_rect(
            "Drag enabled",
            "black",
            text_h,
        )
        god.assets.font.font.outline = 0
        drag_tex_outline.draw(None, drag_rect_outline.move_to(center=drag_rect.center))
        drag_tex.draw(None, drag_rect)

    def render_edit_trajectory(self):
        text_h = god.windowing.width * constants.UI_EDIT_TRAJECTORY_TEXT_H
        error = god.rendering.edit_trajectory_too_far_units is not None
        extra = (
            "Take From"
            if god.player.edit_trajectory_kind == constants.INVENTORY_KIND_INPUT
            else "Put Into"
        )
        text = f"Edit: Bot {god.player.edit_trajectory_kind.title()} ({extra})"
        kind_tex, kind_rect = god.assets.font.get_texture_and_rect(
            text,
            constants.GREEN_GOOD
            if god.rendering.edit_trajectory_hover_available
            == constants.BUILDING_STATUS_AVAILABLE
            else constants.RED_BAD,
            text_h,
        )
        error_text = ""
        error_rect = error_rect_outline = kind_rect
        error_tex = error_tex_outline = kind_tex
        if error:
            error_text = f"Trajectory is {god.rendering.edit_trajectory_too_far_units} units too long"
            error_tex, error_rect = god.assets.font.get_texture_and_rect(
                error_text, constants.TRAJECTORY_ERROR_COLOR, text_h
            )
        god.assets.font.font.outline = 1
        kind_tex_outline, kind_rect_outline = god.assets.font.get_texture_and_rect(
            text,
            "black",
            text_h,
        )
        if error:
            error_tex_outline, error_rect_outline = (
                god.assets.font.get_texture_and_rect(error_text, "black", text_h)
            )
        god.assets.font.font.outline = 0
        other = shared.other_kind(god.player.edit_trajectory_kind)
        help_tex, help_rect = god.assets.font.get_texture_and_rect(
            f"Middle click to edit {other}\nRight click endpoint to select it\nRight click bot to remove trajectory",
            constants.UI_INFO_DESCR_COL,
            text_h,
        )
        kind_rect = kind_rect.move_to(
            midbottom=(
                god.user_input.mouse_screen.x,
                god.user_input.mouse_screen.y - constants.UI_CURSOR_OFFSET * 2,
            )
        )
        kind_tex_outline.draw(None, kind_rect_outline.move_to(center=kind_rect.center))
        kind_tex.draw(None, kind_rect)
        if error:
            error_rect = error_rect.move_to(midbottom=kind_rect.midtop)
            error_tex_outline.draw(
                None, error_rect_outline.move_to(center=error_rect.center)
            )
            error_tex.draw(None, error_rect)
        help_tex.draw(
            None,
            help_rect.move_to(
                midtop=(
                    god.windowing.width / 2,
                    constants.UI_CURSOR_OFFSET,
                )
            ),
        )

    def render_craft_queue(self):
        slot_size = god.windowing.width * constants.UI_CRAFT_QUEUE_SLOT_SIZE_MULT
        for i, craft_item in enumerate(god.player.craft_queue):
            rect = pygame.Rect(
                self.b,
                god.windowing.height - (slot_size + self.b) * (i + 1) - self.b,
                slot_size,
                slot_size,
            )
            self.inventory.render_slot(
                rect,
                craft_item,
                ghost=craft_item.phantom,
                can_hover=False,
                amount_at_two=True,
                image_percentage=(
                    1
                    if craft_item.start_time is None
                    else (god.world.get_ticks() - craft_item.start_time)
                    / (craft_item.item.create_data.time_s * 1000)
                ),
            )

    def render_hotbar(self):
        slot_size = god.windowing.width * constants.UI_HOTBAR_SLOT_SIZE_MULT
        hotbar_width = slot_size * constants.INVENTORY_HOTBAR_SIZE + self.b * (
            constants.INVENTORY_HOTBAR_SIZE - 1
        )
        self.hotbar_rect = pygame.Rect(
            god.windowing.width / 2 - hotbar_width / 2,
            god.windowing.height - self.b - slot_size,
            hotbar_width,
            slot_size,
        )
        hovering_slot = None
        for i, slot in enumerate(god.player.hotbar):
            rect = pygame.Rect(
                self.hotbar_rect.left + i * (slot_size + self.b),
                self.hotbar_rect.top,
                slot_size,
                slot_size,
            )
            hovering_slot = self.inventory.render_slot(
                rect,
                slot,
                hovering_slot,
                "link",
                can_hover=not self.any_menu_open,
                render_at_zero=True,
            )
            if hovering_slot is not None:
                self.cursor = constants.CURSOR_HOVER
        if (
            not self.any_menu_open
            and self.cursor != constants.CURSOR_HOVER
            and self.hotbar_rect.collidepoint(god.user_input.mouse_screen)
        ):
            self.cursor = constants.CURSOR_IDLE_UI
        return hovering_slot

    def render_time_pause_overlay(self):
        self.pause_overlay_tex.draw(None, god.windowing.viewport)
        god.assets.border_overlay.color = constants.UI_PAUSE_OVERLAY_COL
        god.assets.border_overlay.alpha = constants.OPAQUE
        god.assets.border_overlay.draw(None, god.windowing.viewport)

    def render_damage_overlay(self):
        overlay = god.assets.border_overlay
        overlay.color = constants.RED_BAD
        overlay.alpha = int(
            (
                (
                    constants.DAMAGE_OVERLAY_DISAPPEAR_COOLDOWN
                    - (god.world.get_ticks() - god.player.damage_time)
                )
                / constants.DAMAGE_OVERLAY_DISAPPEAR_COOLDOWN
            )
            * 255
        )
        overlay.draw(
            pygame.Rect(
                0,
                0,
                overlay.width * constants.UI_DAMAGE_OVERLAY_ZOOM,
                overlay.height * constants.UI_DAMAGE_OVERLAY_ZOOM,
            ).move_to(center=(overlay.width / 2, overlay.height / 2)),
            god.windowing.viewport,
        )

    def render(self):
        hovering_slot = None
        crafting_slot = False
        self.cursor = constants.CURSOR_IDLE_WORLD
        self.b = god.windowing.width * (constants.UI_BORDER_PERCENT / 100)
        if god.player.edit_trajectory_bot is not None:
            self.render_edit_trajectory()
        elif god.user_input.drag_enabled:
            self.render_drag_enabled()
        right = self.render_stats()
        self.render_debug_indicators(right)
        self.render_craft_queue()
        hotbar_hovered_slot = self.render_hotbar()
        if hotbar_hovered_slot:
            hovering_slot = hotbar_hovered_slot
        prev_ray = self.ui_raycast
        self.ui_raycast = None
        cont = pygame.Rect()
        if self.inventory_open:
            cont, hovering_slot = self.inventory.render(self.b)
            if cont.collidepoint(god.user_input.mouse_screen):
                self.ui_raycast = constants.UI_RAYCAST_EMPTY
                self.cursor = constants.CURSOR_IDLE_UI
            if hovering_slot:
                self.cursor = constants.CURSOR_HOVER
            if self.overlay_menu_func is None and self.open_interface is not None:
                slot = self.open_interface.render(
                    self.b, pygame.Rect(cont.x + cont.w / 2, cont.y, cont.w / 2, cont.h)
                )
                if slot is not None:
                    hovering_slot = slot
                    self.cursor = constants.CURSOR_HOVER
                    if self.open_interface.display_recipe:
                        crafting_slot = True
            if self.overlay_menu_func is not None:
                slot = self.overlay_menu_func(cont)
                if slot is not None:
                    hovering_slot = slot
                    self.cursor = constants.CURSOR_HOVER
                    if self.open_interface.display_recipe:
                        crafting_slot = True
            if self.inventory.left_panning or self.inventory.right_panning:
                self.cursor = constants.CURSOR_HOVER
        elif self.research_open:
            crafting_slot = True
            cont, hovering_slot = self.research.render(self.b)
            if (
                cont.collidepoint(god.user_input.mouse_screen)
                or god.user_input.research_dragging
            ):
                self.ui_raycast = constants.UI_RAYCAST_EMPTY
                self.cursor = constants.CURSOR_HOVER
        if hovering_slot is not None:
            if hovering_slot.empty and (
                hotbar_hovered_slot is None or hotbar_hovered_slot.item is None
            ):
                if hovering_slot.filter:
                    self.ui_raycast = UIRaycastHit(
                        None,
                        False,
                        0,
                        constants.RAYCAST_UI_SLOT_FILTER,
                        hovering_slot.filter,
                    )
            else:
                self.ui_raycast = UIRaycastHit(
                    hovering_slot.item,
                    crafting_slot,
                    hovering_slot.amount,
                    constants.RAYCAST_UI_ITEM,
                    hovering_slot.filter,
                )
        if (
            self.ui_raycast != prev_ray
            and not cont.collidepoint(god.user_input.mouse_screen)
            and not god.user_input.research_dragging
        ):
            pygame.event.post(
                pygame.Event(
                    pygame.MOUSEBUTTONUP, button=pygame.BUTTON_LEFT, emulated=True
                )
            )
        self.raycast_info.render(self.b)
        if self.inventory.floating_slot.source_slot is not None:
            self.render_floating_slot(cont)
        if (
            god.world.get_ticks() - god.player.damage_time
            < constants.DAMAGE_OVERLAY_DISAPPEAR_COOLDOWN
        ):
            self.render_damage_overlay()
        if god.world.paused:
            self.render_time_pause_overlay()
        pygame.mouse.set_cursor(self.cursor)

    def render_floating_slot(self, cont: pygame.Rect):
        rect = god.player.inventory_slots[0].hitbox.move_to(
            center=god.user_input.mouse_screen
        )
        self.inventory.render_slot(
            rect,
            self.inventory.floating_slot,
            None,
            render_bg=False,
        )
        if not cont.collidepoint(god.user_input.mouse_screen) and self.inventory_open:
            icon = god.assets.icons_texs["drop"]
            icon.color = constants.GREEN_GOOD
            icon.alpha = constants.UI_SLOT_GHOST_ALPHA
            icon.draw(
                None,
                rect.move_to(
                    width=rect.w / 1.5,
                    height=rect.h / 1.5,
                    center=(rect.centerx, rect.centery + rect.h),
                ),
            )
