import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui import buildings
from src.client.ui.panel import render_panel_bg, render_panel_outline
from src.client.ui.raycast_info import RaycastInfoUI
from src.client.ui.inventory import FloatingSlot
from src.client.world.chunk import BuildingDataHolder
from src.client.ui.crafting import CraftingInterface
from src.client.ui.building import BuildingInterface
from src.client.ui.inventory import InventoryInterface


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
        self.renderer = renderer
        self.b = 0
        self.raycast_info = RaycastInfoUI()
        self.inventory = InventoryInterface()
        self.crafting_interface = CraftingInterface()
        self.cursor = constants.CURSOR_IDLE_WORLD
        self.overlay_menu_func = None
        self.building_interfaces: dict[str, BuildingInterface] = (
            BuildingInterface.get_interfaces()
        )
        assert buildings

    def mouse_clicked(self, event: pygame.Event):
        interface_slots = []
        if self.open_interface:
            self.open_interface.mouse_clicked(event)
            interface_slots = self.open_interface.get_slots()
        if self.overlay_menu_func is not None:
            return
        self.inventory.mouse_clicked(event, interface_slots)

    def refresh_building_interact(self, base_data, building_data):
        data_holder = BuildingDataHolder(
            base_data, building_data.get("building_id", None)
        )
        if not self.inventory_open:
            self.inventory_open = True
            god.player.set_building_preview(None)
        old_interface = self.open_interface
        self.open_interface = self.building_interfaces[data_holder.building_od]
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
        for item_name, active, key_num, color in (
            (
                "energy_transmitter",
                god.rendering.energy_debug,
                1,
                constants.ENERGY_DEBUG_COLOR,
            ),
            ("bot", god.rendering.trajectory_debug, 2, constants.TRAJECTORY_COLOR),
        ):
            tex = god.assets.building_preview_texs[item_name]
            tex.alpha = (
                constants.OPAQUE_INDICATOR_ALPHA
                if active
                else constants.GHOST_INDICATOR_ALPHA
            )
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
                god.input.mouse_screen.x,
                god.input.mouse_screen.y - constants.UI_CURSOR_OFFSET * 2,
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

    def render(self):
        self.cursor = constants.CURSOR_IDLE_WORLD
        self.b = god.windowing.width * (constants.UI_BORDER_PERCENT / 100)
        if god.player.edit_trajectory_bot is not None:
            self.render_edit_trajectory()
        right = self.render_stats()
        self.render_debug_indicators(right)
        self.render_craft_queue()
        prev_ray = self.ui_raycast
        self.ui_raycast = None
        cont = pygame.Rect()
        if self.inventory_open:
            cont, hovering_slot = self.inventory.render(self.b)
            crafting_slot = False
            if cont.collidepoint(god.input.mouse_screen):
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
            if hovering_slot is not None:
                if hovering_slot.empty:
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
            if self.inventory.left_panning or self.inventory.right_panning:
                self.cursor = constants.CURSOR_HOVER
        if self.ui_raycast != prev_ray and not cont.collidepoint(
            god.input.mouse_screen
        ):
            pygame.event.post(
                pygame.Event(
                    pygame.MOUSEBUTTONUP, button=pygame.BUTTON_LEFT, emulated=True
                )
            )
        self.raycast_info.render(self.b)
        if self.inventory.floating_slot.source_slot is not None:
            self.render_floating_slot(cont)
        pygame.mouse.set_cursor(self.cursor)

    def render_floating_slot(self, cont: pygame.Rect):

        rect = god.player.inventory_slots[0].hitbox.move_to(
            center=god.input.mouse_screen
        )
        self.inventory.render_slot(
            rect,
            self.inventory.floating_slot,
            None,
            render_bg=False,
        )
        if not cont.collidepoint(god.input.mouse_screen):
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

    def can_interact_world(self):
        return not self.inventory_open or self.ui_raycast is None

    def toggle_inventory(self, manual=False):
        if not self.inventory_open:
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
            if isinstance(self.open_interface, BuildingInterface):
                self.open_interface.unsubscribe()
            self.open_interface = None
            self.inventory.floating_slot = FloatingSlot(None, 0)
            self.overlay_menu_func = None
        self.inventory_open = not self.inventory_open
