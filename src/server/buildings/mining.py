from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.shared import Slot
from src.object_data import ItemOD, TileOD, VegetationOD
from src.server.building import StaticBuildingExt
from src.server.inventory import BuildingInventory


class NyliumHarvester(StaticBuildingExt, name_id="nylium_harvester"):
    def init(self):
        out_inv = BuildingInventory(self)
        for i in range(2):
            out_inv.add_slot(Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0))
        self.inventories["out"] = out_inv
        self.working = False
        self.work_start_time = god.world.get_ticks()
        self.plant_item: ItemOD = ItemOD.objects.nylium_fiber
        self.plant: VegetationOD = VegetationOD.objects.nylium_grass

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
        self.out_inv.add(self.plant_item, 1, ignore_filters=True)
        if not self.try_to_work():
            self.stop_working()

    def try_to_work(self):
        if not self.building.has_energy or self.building.moldy:
            return False
        if not self.out_inv.has_space(self.plant_item, 1):
            return False
        self.working = True
        self.work_start_time = god.world.get_ticks()
        self.building.change_state("on", refresh_interact=True)
        timerc.add(self.plant.harvester_time_s, self.on_finish_work)
        return True

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        return data

    def get_extra_raycast_data(self):
        slots = [
            ["text", constants.UI_INFO_DESCR_COL, "(empty)"]
            if self.out_inv.empty
            else ["item", self.plant_item.uid, self.out_inv.count(self.plant_item)]
        ]
        if not self.out_inv.has_space(self.plant_item, 1):
            slots.append(["text", constants.RED_BAD, "Full"])
        if self.working:
            slots.append(
                [
                    "progress",
                    (god.world.get_ticks() - self.work_start_time)
                    / 1000
                    / self.plant.harvester_time_s,
                    "harvest",
                ]
            )
        return [
            [
                "Harvested",
                slots,
            ]
        ]


class Miner(StaticBuildingExt, name_id="miner"):
    def init(self):
        out_inv = BuildingInventory(self)
        for i in range(2):
            out_inv.add_slot(Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0))
        self.inventories["out"] = out_inv
        self.working = False
        self.work_start_time = god.world.get_ticks()
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

    def on_mold_purge(self):
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
        if not self.building.has_energy or self.building.moldy:
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
        self.work_start_time = god.world.get_ticks()
        self.work_time = tile.miner_time_s
        self.building.change_state("on", refresh_interact=True)
        timerc.add(tile.miner_time_s, self.on_finish_work)
        return True

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["work_time"] = self.work_time
        return data

    def get_extra_raycast_data(self):
        mining = []
        space = True
        for tile_data in self.tile_datas:
            drop = TileOD.get(tile_data[0]).item_drop[0][0]
            if drop not in mining:
                mining.append((drop, tile_data[2]))
                if not self.out_inv.has_space(drop, 1, ignore_filters=True):
                    space = False
        slots = []
        for drop, available in mining:
            slots.append(["item", drop.uid, self.out_inv.count(drop)])
            slots.append(["text", "white", f"Available: {available}"])
        if not space:
            slots.append(["text", constants.RED_BAD, "Full"])
        if self.working:
            slots.append(
                [
                    "progress",
                    (god.world.get_ticks() - self.work_start_time)
                    / 1000
                    / self.work_time,
                    "drill",
                ]
            )
        return [
            [
                "Mines",
                slots,
            ]
        ]