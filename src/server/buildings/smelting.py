from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.shared import Slot
from src.object_data import ItemOD
from src.server.building import StaticBuildingExt
from src.server.inventory import BuildingInventory


class Furnace(StaticBuildingExt, name_id="furnace"):
    def init(self):
        self.in_slot = Slot(
            None, 0, [constants.INVENTORY_FILTER_CATEGORY, ["smeltables"]], 0
        )
        self.out_slot = Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0)
        self.inventories["in"] = BuildingInventory(self, self.in_slot)
        self.inventories["out"] = BuildingInventory(self, self.out_slot)
        self.working = False
        self.work_start_time = god.world.get_ticks()
        self.smelt_result: ItemOD | None = None

    def on_inventory_dirty(self):
        if not self.working:
            self.try_to_work()
        self.building.refresh_interact()

    def on_energy_awake(self):
        if not self.working:
            self.try_to_work()

    def on_mold_purge(self):
        if not self.working:
            self.try_to_work()

    def stop_working(self):
        self.working = False
        self.building.change_state("off")

    def on_finish_work(self):
        if self.destroyed:
            return
        self.out_inv.add(self.smelt_result, 1, ignore_filters=True)
        if not self.try_to_work():
            self.stop_working()

    def try_to_work(self):
        if not self.building.has_energy or self.building.moldy:
            return False
        if self.in_inv.empty:
            return False
        smeltable = self.in_inv.slot.item
        smelt_result = smeltable.smelt_result
        if smelt_result is None or smelt_result.create_data.type != "furnace":
            return False
        if not self.out_inv.has_space(smelt_result, 1):
            return False
        self.working = True
        self.work_start_time = god.world.get_ticks()
        self.smelt_result = smelt_result
        self.building.change_state("on")
        self.in_inv.remove(smeltable, 1)
        timerc.add(smelt_result.create_data.time_s, self.on_finish_work)
        return True

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["work_time"] = self.smelt_result.create_data.time_s if self.working else 0
        return data

    def get_extra_raycast_data(self):
        contains_indicators = []
        if not self.in_inv.empty:
            contains_indicators.append(
                [
                    "item",
                    self.in_slot.item.uid,
                    self.in_slot.amount,
                ]
            )
        elif self.out_inv.empty:
            contains_indicators.append(["text", constants.UI_INFO_DESCR_COL, "(empty)"])
        if not self.out_inv.empty:
            contains_indicators.append(
                [
                    "item",
                    self.out_slot.item.uid,
                    self.out_slot.amount,
                ]
            )
        smelting_indicators = []
        if self.working:
            smelting_indicators.append(["item", self.smelt_result.uid, None])
            smelting_indicators.append(
                [
                    "progress",
                    (god.world.get_ticks() - self.work_start_time)
                    / 1000
                    / self.smelt_result.create_data.time_s,
                    "smelt",
                ]
            )
        else:
            if not self.out_inv.empty and not self.out_inv.has_space(
                self.out_slot.item, 1, True
            ):
                smelting_indicators.append(
                    ["text", constants.RED_BAD, "Output is full"]
                )
            elif not self.building.has_energy:
                smelting_indicators.append(
                    [
                        "text",
                        constants.YELLOW_WARNING,
                        "Empty/bad input",
                    ]
                )
        return (
            [
                [
                    "Contains",
                    contains_indicators,
                ],
                ["Smelting", smelting_indicators],
            ]
            if len(smelting_indicators) > 0
            else [
                [
                    "Contains",
                    contains_indicators,
                ]
            ]
        )
