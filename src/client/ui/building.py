import typing

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import BuildingOD, ItemOD
from src.client.world.chunk import BuildingDataHolder


class BuildingInterface:
    _registered_interfaces_: dict[str, type[typing.Self]] = {}
    building_od: BuildingOD

    def __init__(self):
        self.b = 0
        self.building_data: BuildingDataHolder = None
        self.inventories: dict[str, list[shared.Slot]] = {
            "in": None,
            "out": None,
            "upgrade": None,
        }

    def __init_subclass__(cls, name_id: str):
        BuildingInterface._registered_interfaces_[name_id] = cls

    @staticmethod
    def get_interfaces():
        classes = {}
        for name, cls in BuildingInterface._registered_interfaces_.items():
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

    def render_energy_status(self, title_bottom, cont: pygame.Rect):
        title_h = cont.w * constants.UI_INVENTORY_TEXT_H_MULT
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            "Has energy" if self.building_data.has_energy else "No energy",
            constants.GREEN_GOOD
            if self.building_data.has_energy
            else constants.RED_BAD,
            title_h,
        )
        title_tex.draw(
            None, title_rect.move_to(midtop=(cont.centerx, title_bottom + self.b))
        )
        return title_bottom + title_rect.h + self.b * 2

    def render_icon_progress(self, icon, rect, progress_active, start_time, time_s):
        icon.alpha = constants.UI_INTERFACE_ICON_ALPHA
        icon.draw(None, rect)
        icon.alpha = 255
        if progress_active:
            mult = (pygame.time.get_ticks() - start_time) / (time_s * 1000)
            perc_source_h = icon.height * mult
            perc_icon_h = rect.w * mult
            icon.draw(
                pygame.Rect(0, icon.height - perc_source_h, icon.height, perc_source_h),
                rect.move_to(height=perc_icon_h).move(0, rect.w - perc_icon_h),
            )

    def refresh_inventories_data(self, base_data: BuildingDataHolder, building_data):
        self.building_data = base_data
        for name, slots in building_data["inventories"].items():
            if slots is None:
                self.inventories[name] = None
            else:
                if self.inventories[name] is not None:
                    for i, slot_data in enumerate(slots):
                        slot = self.inventories[name][i]
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
