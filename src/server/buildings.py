import pygame

from src import shared
from src import constants
from src.timerc import timerc
from src.object_data import ItemOD
from src.server.building import BuildingExt
from src.server.inventory import BuildingInventory


class Lamp(BuildingExt, name_id="lamp"):
    def on_energy_awake(self):
        self.building.change_state("on")

    def on_energy_sleep(self):
        self.building.change_state("off")


class Storage(BuildingExt, name_id="storage"):
    def init(self):
        self.inventory = BuildingInventory(self)
        for i in range(constants.INVENTORY_ROWS * constants.INVENTORY_COLS):
            self.inventory.add_slot(shared.Slot(None, 0, None, i))
        self.inventories["in"] = self.inventory
        self.inventories["out"] = self.inventory


class Hopper(BuildingExt, name_id="hopper"):
    def init(self):
        self.slot = shared.Slot(None, 0, None, 0)
        self.inventories["in"] = BuildingInventory(self, self.slot)
        self.inventories["out"] = BuildingInventory(self, self.slot)


class Furnace(BuildingExt, name_id="furnace"):
    def init(self):
        self.in_slot = shared.Slot(
            None, 0, [constants.INVENTORY_FILTER_CATEGORY, ["smeltables"]], 0
        )
        self.out_slot = shared.Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0)
        self.inventories["in"] = BuildingInventory(self, self.in_slot)
        self.inventories["out"] = BuildingInventory(self, self.out_slot)
        self.working = False
        self.work_start_time = pygame.time.get_ticks()
        self.smelt_result: ItemOD = None

    def on_inventory_dirty(self):
        if not self.working:
            self.try_to_work()
        self.building.refresh_interact()

    def on_energy_awake(self):
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
        if not self.building.has_energy:
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
        self.work_start_time = pygame.time.get_ticks()
        self.smelt_result = smelt_result
        self.building.change_state("on")
        self.in_inv.remove(smeltable, 1)
        timerc.add(smelt_result.create_data.time_s, self.on_finish_work)
        return True

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["smelt_time"] = self.smelt_result.create_data.time_s if self.working else 0
        return data
