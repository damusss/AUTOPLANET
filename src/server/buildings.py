import pygame

from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.object_data import ItemOD, TileOD
from src.server.building import BuildingExt, MovingBuildingExt
from src.server.inventory import BuildingInventory


class Bot(MovingBuildingExt, name_id="bot"):
    def init(self):
        self.slot = shared.Slot(None, 0, None, 0)
        self.inventory = BuildingInventory(self, self.slot)
        self.upgrade_slot = shared.Slot(
            None, 0, [constants.INVENTORY_FILTER_CATEGORY, ["bot_upgrades"]], 0
        )
        self.inventories["in"] = self.inventory
        self.inventories["out"] = self.inventory
        self.inventories["upgrade"] = BuildingInventory(self, self.upgrade_slot)
        self.filter: ItemOD | None = None

    def on_client_config(self, mail):
        if mail.missing_fields("filter_uid"):
            return
        if mail.filter_uid is None:
            self.filter = None
            self.slot.filter = None
        else:
            self.filter = ItemOD.get(mail.filter_uid)
            self.slot.filter = [
                constants.INVENTORY_FILTER_WHITELIST,
                [self.filter.name_id],
            ]
        self.building.refresh_interact()

    def get_display_data(self):
        return None if self.slot.empty else self.slot.item.uid

    def on_reach(self, target, kind):
        if kind == constants.INVENTORY_KIND_INPUT:
            target_inv = target.ext.inventories["out"]
            if target_inv is None:
                return
            if self.inventory.empty:
                if self.filter is None:
                    item = None
                    for slot in target_inv.slots:
                        if not slot.empty:
                            item = slot.item
                            break
                else:
                    item = self.filter
                if item is None:
                    return
                will_take_amount = min(item.stack_size, target_inv.count(item))
                if will_take_amount <= 0:
                    return
                target_inv.remove(item, will_take_amount)
                self.inventory.add(item, will_take_amount)
            else:
                if not self.slot.check_filter(self.slot.item):
                    return
                can_take_amount = self.slot.item.stack_size - self.slot.amount
                will_take_amount = min(
                    can_take_amount, target_inv.count(self.slot.item)
                )
                target_inv.remove(self.slot.item, will_take_amount)
                self.inventory.add(self.slot.item, will_take_amount)
        elif kind == constants.INVENTORY_KIND_OUTPUT:
            target_inv = target.ext.inventories["in"]
            if target_inv is None:
                return
            not_added = target_inv.add(self.slot.item, self.slot.amount)
            if not_added != self.slot.amount:
                self.inventory.remove(self.slot.item, self.slot.amount - not_added)

    def get_client_data(self):
        data = self.get_inventories_data()
        data["filter"] = self.filter.uid if self.filter is not None else None
        return data


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


class Miner(BuildingExt, name_id="miner"):
    def init(self):
        self.inventories["out"] = BuildingInventory(self)
        for i in range(2):
            self.inventories["out"].add_slot(
                shared.Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0)
            )
        self.working = False
        self.work_start_time = pygame.time.get_ticks()
        self.tile_datas = []
        self.raycasts = []
        for pos in [
            (self.building.hitbox.centerx - 0.5, self.building.hitbox.bottom + 0.5),
            (self.building.hitbox.centerx + 0.5, self.building.hitbox.bottom + 0.5),
        ]:
            ray = god.world.raycast(pos, constants.RAYCASTFLAG_COLLIDER)
            self.tile_datas.append(ray.tile_data)
            self.raycasts.append(ray)
        self.next_tile_data_i = 0
        self.work_time = 0

    def on_inventory_dirty(self):
        if not self.working:
            self.try_to_work()
        self.building.refresh_interact()

    def on_energy_awake(self):
        if not self.working:
            self.try_to_work()

    def stop_working(self):
        self.working = False
        self.building.change_state("off")

    def on_finish_work(self):
        if self.destroyed:
            return
        tile, drop, ore = self.get_tile_drop_item_and_ore()
        self.out_inv.add(drop[0], drop[1], ignore_filters=True)
        self.tile_datas[self.next_tile_data_i][2] = ore - 1
        self.toggle_tile_data()
        if not self.try_to_work():
            self.stop_working()

    def toggle_tile_data(self):
        if self.next_tile_data_i == 0:
            self.next_tile_data_i = 1
        else:
            self.next_tile_data_i = 0

    def get_tile_drop_item_and_ore(self):
        tile_data = self.tile_datas[self.next_tile_data_i]
        tile = TileOD.get(tile_data[0])
        drop = tile.item_drop
        if drop is None:
            return None
        drop = drop[0]
        return tile, drop, tile_data[2]

    def try_to_work(self):
        if not self.building.has_energy:
            return False
        tile, drop, ore = self.get_tile_drop_item_and_ore()
        if drop is None:
            return False
        if ore <= 0:
            god.world.break_raycast(self.raycasts[self.next_tile_data_i])
            return False
        if not self.out_inv.has_space(drop[0], drop[1]):
            self.toggle_tile_data()
            tile, drop, ore = self.get_tile_drop_item_and_ore()
            if drop is None:
                return False
            if ore <= 0:
                god.world.break_raycast(self.raycasts[self.next_tile_data_i])
                return False
            if not self.out_inv.has_space(drop[0], drop[1]):
                return False
        self.working = True
        self.work_start_time = pygame.time.get_ticks()
        self.work_time = tile.miner_time_s
        self.building.change_state("on")
        timerc.add(tile.miner_time_s, self.on_finish_work)
        return True

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["work_time"] = self.work_time
        return data


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
        data["work_time"] = self.smelt_result.create_data.time_s if self.working else 0
        return data
