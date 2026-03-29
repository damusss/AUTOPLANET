import pygame

from src import shared
from src import constants
from src.client import god
from src.client.ui.building import BuildingInterface


class StorageInterface(BuildingInterface, name_id="storage"):
    def render(self, b, cont):
        title_bottom = self.render_title(cont, b)
        slot_b = self.b
        slot_size = god.ui.inventory.slot_size
        pad = cont.w * constants.UI_INVENTORY_PADDING_MULT * 2
        slot_i = 0
        hovering_slot = None
        slots = self.inventories["in"]
        for i in range(constants.INVENTORY_ROWS):
            for j in range(constants.INVENTORY_COLS):
                slot_hitbox = pygame.Rect(
                    cont.x
                    + cont.w / 2
                    - (
                        (
                            slot_size * constants.INVENTORY_COLS
                            + slot_b * (constants.INVENTORY_COLS - 1)
                        )
                        / 2
                    )
                    + (slot_size + slot_b) * j,
                    title_bottom + pad + (slot_size + slot_b) * i,
                    slot_size,
                    slot_size,
                )
                hovering_slot = god.ui.inventory.render_slot(
                    slot_hitbox,
                    slots[slot_i],
                    hovering_slot,
                    ghost=(god.ui.inventory.floating_slot.source_slot is slots[slot_i]),
                )
                slot_i += 1


class HopperInterface(BuildingInterface, name_id="hopper"):
    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        slot_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=cont.center)
        slot = self.inventories["in"][0]
        return god.ui.inventory.render_slot(
            slot_rect,
            slot,
            None,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot,
        )


class FurnaceInterface(BuildingInterface, name_id="furnace"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = pygame.time.get_ticks()
        self.smelt_time = 0

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.smelt_time = building_data["smelt_time"]

    def render(self, b, cont):
        self.render_title(cont, b)
        left = (cont.centerx - cont.w / 4, cont.centery)
        right = (cont.centerx + cont.w / 4, cont.centery)
        slot_size = god.ui.inventory.slot_size * 1.5
        left_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=left)
        right_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=right)
        left_slot = self.inventories["in"][0]
        right_slot = self.inventories["out"][0]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            left_rect,
            left_slot,
            hovering,
            empty_icon="ore",
            ghost=(god.ui.inventory.floating_slot.source_slot is left_slot),
        )
        hovering = god.ui.inventory.render_slot(
            right_rect,
            right_slot,
            hovering,
            empty_icon="metal",
            ghost=(god.ui.inventory.floating_slot.source_slot is right_slot),
        )
        fire_icon = god.assets.icons_texs["smelt"]
        icon_size = god.ui.inventory.slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(center=cont.center)
        self.render_icon_progress(
            fire_icon, icon_rect, self.working, self.work_start_time, self.smelt_time
        )
        return hovering
