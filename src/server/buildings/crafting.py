from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.shared import Slot
from src.object_data import ItemOD
from src.server.building import BuildingExt
from src.server.inventory import BuildingInventory


class Crafter(BuildingExt, name_id="crafter"):
    def init(self):
        in_inv = BuildingInventory(self)
        for i in range(constants.CRAFTER_INVENTORY_SIZE):
            in_inv.add_slot(Slot(None, 0, None, i))
        self.inventories["in"] = in_inv
        self.out_slot = Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0)
        self.inventories["out"] = BuildingInventory(self, self.out_slot)
        self.working = False
        self.work_start_time = god.world.get_ticks()
        self.recipe: ItemOD | None = None

    def on_client_config(self, mail):
        if mail.missing_fields("recipe_uid"):
            return
        if mail.recipe_uid is None:
            self.recipe = None
            self.stop_working()
        else:
            self.recipe = ItemOD.get(mail.recipe_uid)
            if not self.working:
                self.try_to_work()
        self.building.refresh_interact()
        self.building.chunk.refresh()

    def get_config(self):
        return {"recipe_uid": ItemOD.uid_or_none(self.recipe)}

    def on_inventory_dirty(self):
        if not self.working:
            self.try_to_work()
        self.building.refresh_interact()

    def try_to_work(self):
        if not self.building.has_energy:
            return False
        if self.recipe is None:
            return False
        if not self.out_inv.has_space(self.recipe, 1):
            return False
        craft_status = shared.craft_availability_status(
            self.recipe, self.in_inv.count, 1
        )
        if craft_status.availability != constants.CRAFT_READY:
            return False
        self.working = True
        self.work_start_time = god.world.get_ticks()
        self.building.change_state("on")
        for item_uid, amount in craft_status.counted_items.items():
            self.in_inv.remove(ItemOD.get(item_uid), amount)
        timerc.add(self.recipe.create_data.time_s, self.on_finish_work)
        return True

    def on_finish_work(self):
        if self.destroyed:
            return
        self.out_inv.add(self.recipe, 1, ignore_filters=True)
        if not self.try_to_work():
            self.stop_working()

    def on_energy_awake(self):
        if not self.working:
            self.try_to_work()

    def stop_working(self):
        self.working = False
        self.building.change_state("off")

    def get_client_data(self):
        data = self.get_inventories_data()
        data.update(self.get_config())
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        return data

    def get_extra_data(self):
        return {
            "working": self.working,
            "recipe_uid": self.recipe.uid if self.recipe is not None else None,
            "work_start_time": shared.eval_delta(self.work_start_time),
        }

    def get_extra_raycast_data(self):
        full = False
        if not self.working and self.recipe is not None:
            if not self.out_inv.has_space(self.recipe, 1, ignore_filters=True):
                full = True
        if self.out_inv.empty:
            out_indicators = [["text", constants.UI_INFO_DESCR_COL, "(empty)"]]
        else:
            out_indicators = []
            for out_slot in self.out_inv.slots:
                if out_slot.empty:
                    continue
                out_indicators.append(["item", out_slot.item.uid, out_slot.amount])
            if full:
                out_indicators.append(["text", constants.RED_BAD, "Full"])
        if self.in_inv.empty:
            in_indicators = [["text", constants.UI_INFO_DESCR_COL, "(empty)"]]
        else:
            in_indicators = []
            for in_slot in self.in_inv.slots:
                if in_slot.empty:
                    continue
                in_indicators.append(["item", in_slot.item.uid, in_slot.amount])
        recipe_indicators = [
            (
                ["text", constants.RED_BAD, "Not set"]
                if self.recipe is None
                else ["item", self.recipe.uid, None]
            )
        ]
        if self.working:
            recipe_indicators.append(
                [
                    "progress",
                    (god.world.get_ticks() - self.work_start_time)
                    / 1000
                    / self.recipe.create_data.time_s,
                    "gear",
                ]
            )
        elif not full and self.recipe is not None and self.building.has_energy:
            recipe_indicators.append(
                [
                    "text",
                    constants.YELLOW_WARNING,
                    "Empty/bad input",
                ]
            )
        return [
            ["Output", out_indicators],
            ["Input", in_indicators],
            ["Recipe", recipe_indicators],
        ]
