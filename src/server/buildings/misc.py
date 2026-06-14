from src import constants
from src.server import god
from src.shared import Slot
from src.timerc import timerc
from src.object_data import ItemOD
from src.server.building import StaticBuildingExt
from src.server.inventory import BuildingInventory


class Lamp(StaticBuildingExt, name_id="lamp"):
    def on_energy_awake(self):
        if not self.building.moldy:
            self.building.change_state("on")

    def on_mold_purge(self):
        if self.building.has_energy:
            self.building.change_state("on")

    def on_energy_sleep(self):
        self.building.change_state("off")

    def on_mold_infect(self):
        self.building.change_state("off")


class MoldSanitizer(StaticBuildingExt, name_id="mold_sanitizer"):
    def init(self):
        self.slot = Slot(
            None, 0, [constants.INVENTORY_FILTER_WHITELIST, ["ammonia"]], 0
        )
        self.inventories["in"] = BuildingInventory(self, self.slot)
        self.working = False
        self.ammonia_od = ItemOD.objects.ammonia

    def on_energy_awake(self):
        if not self.working:
            self.try_to_work()

    def on_mold_purge(self):
        if not self.working:
            self.try_to_work()

    def on_inventory_dirty(self):
        if not self.working:
            self.try_to_work()
        self.building.refresh_interact()

    def on_destroy(self):
        super().on_destroy()
        if self.working:
            god.world.mold.on_destroyed_or_unsanitized(self.building, sanitizer=True)

    def stop_working(self):
        self.working = False
        self.building.change_state("off")
        god.world.mold.on_destroyed_or_unsanitized(self.building, sanitizer=True)
        god.world.mold.on_placed_or_purged_or_sanitized(self.building, purged=True)

    def try_to_work(self):
        if not self.building.has_energy or self.building.moldy:
            return False
        if not self.in_inv.has(self.ammonia_od, 1):
            return False
        was_working = self.working
        self.working = True
        self.in_inv.remove(self.ammonia_od, 1)
        self.building.change_state("on")
        if not was_working:
            god.world.mold.on_placed_or_purged_or_sanitized(
                self.building, sanitizer=True
            )
        timerc.add(constants.MOLD_SANITIZER_CONSUME_TIME, self.on_finish_work)
        return True

    def on_finish_work(self):
        if self.destroyed:
            return
        if not self.try_to_work():
            self.stop_working()

    def get_extra_raycast_data(self):
        return [
            [
                "Ammonia Left",
                [
                    ["text", constants.UI_INFO_DESCR_COL, "(empty)"]
                    if self.in_inv.empty
                    else ["item", self.slot.item.uid, self.slot.amount],
                    [
                        "text",
                        constants.GREEN_GOOD
                        if self.working
                        else constants.YELLOW_WARNING,
                        "Barrier active" if self.working else "Barrier inactive",
                    ],
                ],
            ],
        ]
