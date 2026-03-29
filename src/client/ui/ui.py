import pygame

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


class WorldUI:
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
        self.building_interfaces: dict[str, BuildingInterface] = (
            BuildingInterface.get_interfaces()
        )
        assert buildings

    def mouse_clicked(self, event: pygame.Event):
        interface_slots = []
        if self.open_interface:
            self.open_interface.mouse_clicked(event)
            interface_slots = self.open_interface.get_slots()
        self.inventory.mouse_clicked(event, interface_slots)

    def refresh_building_interact(self, base_data, building_data):
        data_holder = BuildingDataHolder(base_data)
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
            bg_alpha=255,
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
            bg_alpha=255,
            bg_color=constants.UI_ENERGY_COL,
        )
        render_panel_outline(
            (box.x + self.b, box.y + self.b, bar_w, bar_h),
            cs,
            outline_alpha=255,
            outline_color=constants.UI_BARS_OUTLINE_COL,
        )
        render_panel_outline(
            (box.x + self.b, box.y + self.b * 2 + bar_h, bar_w, bar_h),
            cs,
            outline_alpha=255,
            outline_color=constants.UI_BARS_OUTLINE_COL,
        )
        circle = pygame.Rect(box.x + self.b, box.y + self.b, bar_h, bar_h)
        render_panel_bg(circle.inflate(2, 2), cs, 255, constants.UI_BARS_OUTLINE_COL)
        god.assets.health_tex.draw(None, circle.inflate(-4, -4))
        circle = pygame.Rect(
            box.x + self.b, box.y + self.b * 2 + bar_h, bar_h, bar_h
        ).inflate(2, 2)
        render_panel_bg(circle.inflate(2, 2), cs, 255, constants.UI_BARS_OUTLINE_COL)
        god.assets.energy_tex.draw(None, circle.inflate(-4, -4))

        pos_tex, pos_rect = god.assets.font.get_texture_and_rect(
            f"X: {int(god.player.pos.x)} Y: {int(god.player.pos.y)}",
            constants.UI_RAYCAST_INFO_DESCR_COL,
            bar_h,
        )
        pos_tex.draw(None, pos_rect.move_to(topleft=(self.b * 2, box.bottom + self.b)))

    def render_craft_queue(self):
        slot_size = god.windowing.width * constants.UI_CRAFT_QUEUE_SLOT_SIZE_MULT
        width = slot_size * len(god.player.craft_queue) + self.b * (
            len(god.player.craft_queue) - 1
        )
        left = god.windowing.width / 2 - width / 2
        for i, craft_item in enumerate(god.player.craft_queue):
            rect = pygame.Rect(
                left + (slot_size + self.b) * i,
                god.windowing.height - slot_size - self.b,
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
                    else (pygame.time.get_ticks() - craft_item.start_time)
                    / (craft_item.item.create_data.time_s * 1000)
                ),
            )

    def render(self):
        self.cursor = constants.CURSOR_IDLE_WORLD
        self.b = god.windowing.width * (constants.UI_BORDER_PERCENT / 100)
        self.render_stats()
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
            if self.open_interface is not None:
                slot = self.open_interface.render(
                    self.b, pygame.Rect(cont.x + cont.w / 2, cont.y, cont.w / 2, cont.h)
                )
                if slot is not None:
                    hovering_slot = slot
                    self.cursor = constants.CURSOR_HOVER
                    if self.open_interface == self.crafting_interface:
                        crafting_slot = True
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
            self.inventory.render_slot(
                god.player.inventory_slots[0].hitbox.move_to(
                    center=god.input.mouse_screen
                ),
                self.inventory.floating_slot,
                None,
                render_bg=False,
            )
        pygame.mouse.set_cursor(self.cursor)

    def can_interact_world(self):
        return not self.inventory_open or self.ui_raycast is None

    def toggle_inventory(self, manual=False):
        if not self.inventory_open:
            self.open_interface = self.crafting_interface
            god.player.set_building_preview(None)
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
        self.inventory_open = not self.inventory_open
