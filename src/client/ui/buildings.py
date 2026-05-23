import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui.building import BuildingInterface
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
        self.filter: ItemOD = None
        self.filter_rect: pygame.Rect = None
        items = sorted(
            sorted(ItemOD.get_list(), key=lambda item: item.display_name),
            key=lambda item: item.category if item.category is not None else "zzz",
        )
        self.item_slots = [shared.Slot(item, 1) for item in items]
        self.back_btn = IconButton("left-arrow", "0.5", 0.9)
        self.delete_btn = IconButton("delete", "0.5", 0.6)

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.filter = (
            None
            if building_data["filter"] is None
            else ItemOD.get(building_data["filter"])
        )

    def mouse_clicked(self, event: pygame.Event):
        if event.button != pygame.BUTTON_LEFT:
            return
        if god.ui.overlay_menu_func is not None:
            if self.back_btn.clicked(event):
                god.ui.overlay_menu_func = None
            if self.delete_btn.clicked(event):
                god.ui.overlay_menu_func = None
                god.client.conn.mail(
                    constants.MAIL_BUILDING_CONFIG,
                    building_id=self.building_data.id,
                    filter_uid=None,
                )
            for slot in self.item_slots:
                if slot.hitbox.collidepoint(event.pos):
                    god.client.conn.mail(
                        constants.MAIL_BUILDING_CONFIG,
                        building_id=self.building_data.id,
                        filter_uid=slot.item.uid,
                    )
                    god.ui.overlay_menu_func = None
        else:
            if self.filter_rect is None or not self.filter_rect.collidepoint(event.pos):
                return
            god.ui.overlay_menu_func = self.render_filter_selection

    def render_filter_selection(self, cont: pygame.Rect):
        bottom = god.ui.inventory.render_interface_title(
            "Select Filter", cont.topleft, cont.w, 0.5
        )
        pad = cont.w * constants.UI_INVENTORY_PADDING_MULT
        b = self.b
        slots_w = cont.w - pad * 2
        slot_size = god.ui.inventory.slot_size
        slots_per_row = int(slots_w / (slot_size + b))
        slot_b = (slots_w - slots_per_row * slot_size) / (slots_per_row - 1)
        ri = 0
        ii = 0
        hovering = None
        while ii < len(self.item_slots):
            for ci in range(slots_per_row):
                rect = pygame.Rect(
                    cont.x + pad + (slot_size + slot_b) * ci,
                    bottom + pad + (slot_size + slot_b) * ri,
                    slot_size,
                    slot_size,
                )
                hovering = god.ui.inventory.render_slot(
                    rect, self.item_slots[ii], hovering, storage=False
                )
                ii += 1
                if ii >= len(self.item_slots):
                    break
            ri += 1
        left_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomright=(cont.centerx - slot_b, cont.bottom - slot_b)
        )
        right_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomleft=(cont.centerx + slot_b, cont.bottom - slot_b)
        )
        self.back_btn.render(left_rect)
        self.delete_btn.render(right_rect)
        return hovering

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
        self.filter_rect = filter_rect
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
        self.work_start_time = pygame.time.get_ticks()
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


class FurnaceInterface(BuildingInterface, name_id="furnace"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = pygame.time.get_ticks()
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
            fire_icon, icon_rect, self.working, self.work_start_time, self.work_time
        )
        return hovering
