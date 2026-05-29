import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui.building import BuildingInterface, ItemSelectionExtension
from src.client.ui.panel import IconButton


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
        return hovering_slot


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


class BotInterface(BuildingInterface, name_id="bot"):
    def __init__(self):
        super().__init__()
        self.filter: ItemOD | None = None
        items = sorted(
            sorted(ItemOD.get_list(), key=lambda item: item.display_name),
            key=lambda item: item.category if item.category is not None else "zzz",
        )
        self.item_selection = ItemSelectionExtension(
            self, items, self.get_config, "Select Filter"
        )

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.filter = (
            None
            if building_data["filter"] is None
            else ItemOD.get(building_data["filter"])
        )

    def mouse_clicked(self, event: pygame.Event):
        self.item_selection.mouse_clicked(event)

    def get_config(self, item: ItemOD | None):
        return {"filter_uid": None if item is None else item.uid}

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        filter_size = god.ui.inventory.slot_size * 1.5
        slot_rect_1 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            midright=(cont.centerx - b, cont.centery)
        )
        slot_rect_2 = pygame.Rect(0, 0, filter_size, filter_size).move_to(
            midleft=(cont.centerx + b, cont.centery)
        )
        filter_rect = pygame.Rect(0, 0, filter_size, filter_size).move_to(
            center=(cont.centerx, cont.centery - cont.h / 4)
        )
        self.item_selection.enter_selection_rect = filter_rect
        slot_1 = self.inventories["in"][0]
        slot_2 = self.inventories["upgrade"][0]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            slot_rect_1,
            slot_1,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_1,
        )
        hovering = god.ui.inventory.render_slot(
            slot_rect_2,
            slot_2,
            hovering,
            "upgrade",
            ghost=god.ui.inventory.floating_slot.source_slot is slot_2,
        )
        hovering = god.ui.inventory.render_slot(
            filter_rect, shared.Slot(self.filter, 1), hovering, "lock", storage=False
        )
        return hovering


class MinerInterface(BuildingInterface, name_id="miner"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = 0
        self.work_time = 0

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.work_time = building_data["work_time"]

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        slot_rect_1 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            midright=(cont.centerx - b, cont.centery)
        )
        slot_rect_2 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            midleft=(cont.centerx + b, cont.centery)
        )
        slot_1 = self.inventories["out"][0]
        slot_2 = self.inventories["out"][1]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            slot_rect_1,
            slot_1,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_1,
        )
        hovering = god.ui.inventory.render_slot(
            slot_rect_2,
            slot_2,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_2,
        )
        return hovering


class CrafterInterface(BuildingInterface, name_id="crafter"):
    display_recipe = True

    def __init__(self):
        super().__init__()
        self.recipe: ItemOD | None = None
        self.working = False
        self.work_start_time = 0
        items = sorted(
            sorted(
                filter(
                    lambda item: (
                        item.create_data is not None
                        and item.create_data.type in ["hands", "crafter"]
                    ),
                    ItemOD.get_list(),
                ),
                key=lambda item: item.display_name,
            ),
            key=lambda item: item.category if item.category is not None else "zzz",
        )
        self.item_selection = ItemSelectionExtension(
            self, items, self.get_config, "Select Recipe"
        )

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.recipe = (
            ItemOD.get(building_data["recipe_uid"])
            if building_data["recipe_uid"] is not None
            else None
        )

    def mouse_clicked(self, event: pygame.Event):
        self.item_selection.mouse_clicked(event)

    def get_config(self, item: ItemOD | None):
        return {"recipe_uid": None if item is None else item.uid}

    def render(self, b, cont):
        self.render_title(cont, b)
        left = (cont.centerx - cont.w / 4, cont.centery)
        inv_slot_size = god.ui.inventory.slot_size
        left_w = inv_slot_size * 2 + b
        left_h = (inv_slot_size * constants.CRAFTER_INVENTORY_SIZE / 2) + (
            b * (constants.CRAFTER_INVENTORY_SIZE / 2 - 1)
        )
        cur_top = left[1] - left_h / 2
        hovering = None
        for r in range(int(constants.CRAFTER_INVENTORY_SIZE / 2)):
            cur_left = left[0] - left_w / 2
            for c in range(2):
                slot_rect = pygame.Rect(cur_left, cur_top, inv_slot_size, inv_slot_size)
                slot = self.inventories["in"][r * 2 + c]
                hovering = god.ui.inventory.render_slot(
                    slot_rect,
                    slot,
                    hovering,
                    ghost=(god.ui.inventory.floating_slot.source_slot is slot),
                )
                cur_left += inv_slot_size + b
            cur_top += inv_slot_size + b
        recipe_size = god.ui.inventory.slot_size * 1.2
        recipe_rect = pygame.Rect(0, 0, recipe_size, recipe_size).move_to(
            center=(cont.centerx, cont.centery - cont.h / 4)
        )
        self.item_selection.enter_selection_rect = recipe_rect
        hovering = god.ui.inventory.render_slot(
            recipe_rect, shared.Slot(self.recipe, 1), hovering, "select", storage=False
        )
        right = (cont.centerx + cont.w / 4, cont.centery)
        out_slot_size = inv_slot_size * 1.5
        right_rect = pygame.Rect(0, 0, out_slot_size, out_slot_size).move_to(
            center=right
        )
        right_slot = self.inventories["out"][0]
        hovering = god.ui.inventory.render_slot(
            right_rect,
            right_slot,
            hovering,
            ghost=(god.ui.inventory.floating_slot.source_slot is right_slot),
        )
        gear_icon = god.assets.icons_texs["gear"]
        icon_size = inv_slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(center=cont.center)
        self.render_icon_progress(
            gear_icon,
            icon_rect,
            self.working,
            self.work_start_time,
            self.recipe.create_data.time_s if self.recipe is not None else 0,
        )
        return hovering


class FurnaceInterface(BuildingInterface, name_id="furnace"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = 0
        self.work_time = 0

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.work_time = building_data["work_time"]

    def render(self, b, cont):
        self.render_title(cont, b)
        left = (cont.centerx - cont.w / 4, cont.centery)
        right = (cont.centerx + cont.w / 4, cont.centery)
        slot_size = god.ui.inventory.slot_size * 1.5
        left_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=left)
        right_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=right)
        inv_in, inv_out = self.inventories["in"], self.inventories["out"]
        left_slot = inv_in[0]
        right_slot = inv_out[0]
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
            fire_icon, icon_rect, self.working, self.work_start_time, self.work_time
        )
        return hovering
