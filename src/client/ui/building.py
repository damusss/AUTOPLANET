import typing

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import BuildingOD, ItemOD
from src.client.ui.panel import IconButton
from src.client.world.chunk import BuildingDataHolder


class BuildingInterface:
    REGISTERED_INTERFACES: dict[str, type[typing.Self]] = {}
    building_od: BuildingOD
    display_recipe = False

    def __init__(self):
        self.b = 0
        self.building_data: BuildingDataHolder | None = None
        self.inventories: dict[str, list[shared.Slot] | None] = {
            "in": None,
            "out": None,
            "upgrade": None,
        }

    def __init_subclass__(cls, name_id: str):
        BuildingInterface.REGISTERED_INTERFACES[name_id] = cls

    @staticmethod
    def get_interfaces():
        classes = {}
        for name, cls in BuildingInterface.REGISTERED_INTERFACES.items():
            obj = cls()
            obj.building_od = BuildingOD.get(name)
            classes[obj.building_od] = obj
        return classes

    def get_slots(self):
        total = []
        for slots in self.inventories.values():
            if slots is None:
                continue
            total += slots
        return total

    def mouse_clicked(self, event: pygame.Event): ...

    def render(self, b, cont: pygame.Rect): ...

    def render_title(self, cont: pygame.Rect, b):
        self.b = b
        bottom = god.ui.inventory.render_interface_title(
            self.building_data.building_od.display_name, cont.topleft, cont.w
        )
        if self.building_od.need_energy:
            bottom = self.render_energy_status(bottom, cont)
        return bottom

    def render_energy_status(self, bottom, cont: pygame.Rect):
        text_h = cont.w * constants.UI_INVENTORY_TEXT_H_MULT
        energy_tex, energy_rect = god.assets.font.get_texture_and_rect(
            "Has energy" if self.building_data.has_energy else "No energy",
            constants.GREEN_GOOD
            if self.building_data.has_energy
            else constants.RED_BAD,
            text_h,
        )
        energy_rect = energy_rect.move_to(midtop=(cont.centerx, bottom + self.b))
        bottom = energy_rect.bottom + self.b
        energy_tex.draw(None, energy_rect)
        if self.building_data.moldy:
            mold_tex, mold_rect = god.assets.font.get_texture_and_rect(
                "Moldy", constants.RED_BAD, text_h
            )
            mold_rect = mold_rect.move_to(midtop=(cont.centerx, bottom + self.b))
            bottom = mold_rect.bottom + self.b
            mold_tex.draw(None, mold_rect)
        return bottom

    def render_icon_progress(self, icon, rect, progress_active, start_time, time_s, mult_override=None):
        icon.alpha = constants.UI_INTERFACE_ICON_ALPHA
        icon.draw(None, rect)
        icon.alpha = constants.OPAQUE
        if progress_active and time_s != 0:
            if mult_override is not None:
                mult = mult_override
            else:
                mult = (god.world.get_ticks() - start_time) / (time_s * 1000)
            perc_source_h = icon.height * mult
            perc_icon_h = rect.w * mult
            icon.draw(
                pygame.Rect(0, icon.height - perc_source_h, icon.height, perc_source_h),
                rect.move_to(height=perc_icon_h).move(0, rect.w - perc_icon_h),
            )

    def refresh_inventories_data(self, base_data: BuildingDataHolder, building_data):
        self.building_data = base_data
        for name, slots in building_data["inventories"].items():
            inv = self.inventories[name]
            if slots is None:
                self.inventories[name] = None
            else:
                if inv is not None:
                    for i, slot_data in enumerate(slots):
                        slot = inv[i]
                        prev_amount = slot.amount
                        slot.item = (
                            ItemOD.get(slot_data[0])
                            if slot_data[0] is not None
                            else None
                        )
                        slot.amount = slot_data[1]
                        slot.filter = slot_data[2]
                        slot.cont = f"{self.building_data.id} {name}"
                        if (
                            prev_amount != slot.amount
                            and slot is god.ui.inventory.floating_slot.source_slot
                        ):
                            god.ui.inventory.floating_slot.amount += (
                                slot.amount - prev_amount
                            )
                            if god.ui.inventory.floating_slot.amount <= 0:
                                god.ui.inventory.floating_slot.source_slot = None
                else:
                    self.inventories[name] = [
                        shared.Slot(
                            ItemOD.get(slot[0]) if slot[0] is not None else None,
                            slot[1],
                            slot[2],
                            i,
                            f"{self.building_data.id} {name}",
                        )
                        for i, slot in enumerate(slots)
                    ]

    def refresh_data(self, base_data: BuildingDataHolder, building_data):
        self.refresh_inventories_data(base_data, building_data)

    def unsubscribe(self):
        god.client.conn.mail(
            constants.MAIL_BUILDING_INTERACT,
            building_id=self.building_data.id,
            unsubscribe=True,
        )

    def on_exit(self): ...
    def on_enter(self): ...


class ItemSelectionExtension:
    def __init__(
        self,
        parent: "BuildingInterface",
        items: list[ItemOD],
        get_config_func,
        menu_name,
    ):
        self.enter_selection_rect = None
        self.items = items
        self.parent = parent
        self.get_config_func = get_config_func
        self.menu_name = menu_name
        self.item_slots = [shared.Slot(item, 1) for item in items]
        self.back_btn = IconButton("left_arrow", "0.5", 0.9)
        self.delete_btn = IconButton("delete", "0.5", 0.6)

    def render_item_selection(self, cont: pygame.Rect):
        bottom = god.ui.inventory.render_interface_title(
            self.menu_name, cont.topleft, cont.w, 0.5
        )
        pad = cont.w * constants.UI_INVENTORY_PADDING_MULT
        b = self.parent.b
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
                    building_id=self.parent.building_data.id,
                    **self.get_config_func(None),
                )
            for slot in self.item_slots:
                if slot.hitbox.collidepoint(event.pos):
                    god.client.conn.mail(
                        constants.MAIL_BUILDING_CONFIG,
                        building_id=self.parent.building_data.id,
                        **self.get_config_func(slot.item),
                    )
                    god.ui.overlay_menu_func = None
                    break
        else:
            if (
                self.enter_selection_rect is None
                or not self.enter_selection_rect.collidepoint(event.pos)
            ):
                return
            god.ui.overlay_menu_func = self.render_item_selection
