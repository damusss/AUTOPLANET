from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.shared import Slot
from src.object_data import ItemOD, TileOD
from src.server.building import StaticBuildingExt
from src.server.inventory import BuildingInventory


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


class MoldHarvester(StaticBuildingExt, name_id="mold_harvester"):
    def init(self):
        out_inv = BuildingInventory(self)
        for i in range(2):
            out_inv.add_slot(Slot(None, 0, [constants.INVENTORY_FILTER_READONLY], 0))
        self.in_slot = Slot(
            None, 0, [constants.INVENTORY_FILTER_WHITELIST, ["ammonia"]]
        )
        self.inventories["in"] = BuildingInventory(self, self.in_slot)
        self.inventories["out"] = out_inv
        self.working = False
        self.work_start_time = god.world.get_ticks()
        self.work_time = 0
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
        self.fuel_od = ItemOD.objects.ammonia

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
        if len(self.tile_datas) < 2:
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
        if len(self.tile_datas) <= 0:
            return False
        if not self.building.has_energy or self.building.moldy:
            return False
        if not self.in_inv.has(self.fuel_od, 1):
            return False
        tile, drop, ore = self.get_tile_drop_item_and_ore()
        if drop is None:
            return False
        if ore <= 0:
            self.tile_datas.pop(self.next_tile_data_i)
            self.toggle_tile_data()
            return self.try_to_work()
        if not self.out_inv.has_space(drop[0], drop[1]):
            self.toggle_tile_data()
            tile, drop, ore = self.get_tile_drop_item_and_ore()
            if drop is None:
                return False
            if ore <= 0:
                self.tile_datas.pop(self.next_tile_data_i)
                self.toggle_tile_data()
                return self.try_to_work()
            if not self.out_inv.has_space(drop[0], drop[1]):
                return False
        self.working = True
        self.work_start_time = god.world.get_ticks()
        self.work_time = tile.miner_time_s
        self.in_inv.remove(self.fuel_od, 1)
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
        slots = []
        mold_patch: TileOD = TileOD.objects.mold_patch
        if len(self.tile_datas) > 0:
            drop = mold_patch.item_drop[0][0]
            slots.append(["item", drop.uid, self.out_inv.count(drop)])
            available = 0
            for tile_data in self.tile_datas:
                available += tile_data[2]
            slots.append(["text", "white", f"Available: {available}"])
            if not self.out_inv.has_space(drop, 1):
                slots.append(["text", constants.RED_BAD, "Full"])
        else:
            slots.append(["text", constants.RED_BAD, "No mold available"])
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
                "Contains",
                [
                    ["text", constants.YELLOW_WARNING, "(empty)"]
                    if self.in_inv.empty
                    else ["item", self.in_slot.item.uid, self.in_slot.amount]
                ],
            ],
            [
                "Harvests",
                slots,
            ],
        ]


class MoldMiner(StaticBuildingExt, name_id="mold_miner"):
    def init(self):
        self.in_slot = Slot(
            None, 0, [constants.INVENTORY_FILTER_WHITELIST, ["ammonia"]]
        )
        self.inventories["in"] = BuildingInventory(self, self.in_slot)
        self.progress = 0
        self.working = False
        self.work_start_time = 0
        self.work_time = 0
        self.fuel_od: ItemOD = ItemOD.objects.ammonia
        self.mold_patch_od: TileOD = TileOD.objects.mold_patch

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

    def break_mold(self):
        self.stop_working()
        advance = True
        mold_ray = god.world.raycast(
            (self.building.hitbox.centerx, self.building.hitbox.bottom + 1.5),
            constants.RAYCASTFLAG_COLLIDER,
        )
        if (
            mold_ray is None
            or mold_ray.hitbox is None
            or mold_ray.type != constants.RAYCAST_TILE
            or mold_ray.object_data != self.mold_patch_od
        ):
            advance = False
        if not advance:
            god.world.break_raycast(
                god.world.raycast(
                    (self.building.hitbox.centerx, self.building.hitbox.bottom + 0.5),
                    constants.RAYCASTFLAG_COLLIDER,
                )
            )
            return
        slot_item = self.in_slot.item
        slot_amount = self.in_slot.amount
        self.in_inv.remove(slot_item, slot_amount)
        building_od = self.building.building_od
        hitbox = self.building.hitbox
        clients = self.building.subscribed_client_players.copy()
        god.world.break_building(self.building, tool=False)
        god.world.break_raycast(
            god.world.raycast(
                (self.building.hitbox.centerx, self.building.hitbox.bottom + 0.5),
                constants.RAYCASTFLAG_COLLIDER,
            )
        )
        new_miner = god.world.place_building(
            building_od, (hitbox.centerx, hitbox.centery + hitbox.height / 4)
        )
        new_miner.subscribed_client_players = clients
        miner_ext: MoldMiner = new_miner.ext
        miner_ext.in_slot.item = slot_item
        miner_ext.in_slot.amount = slot_amount
        new_miner.refresh_interact()
        miner_ext.try_to_work()

    def on_finish_work(self):
        if self.destroyed:
            return
        self.progress += 1
        if self.progress >= constants.MOLD_BREAKER_CONSUME_AMOUNT:
            self.break_mold()
            return
        self.building.refresh_interact()
        if not self.try_to_work():
            self.stop_working()

    def try_to_work(self):
        if not self.building.has_energy or self.building.moldy:
            return False
        if not self.in_inv.has(self.fuel_od, 1):
            return False
        self.working = True
        self.work_start_time = god.world.get_ticks()
        self.work_time = self.mold_patch_od.miner_time_s
        self.in_inv.remove(self.fuel_od, 1)
        self.building.change_state("on", refresh_interact=True)
        timerc.add(self.mold_patch_od.miner_time_s, self.on_finish_work)
        return True

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["work_time"] = self.work_time
        data["progress"] = self.progress
        return data

    def get_extra_raycast_data(self):
        progress = self.progress
        if self.working:
            progress += (
                (god.world.get_ticks() - self.work_start_time) / 1000 / self.work_time
            )
        return [
            [
                "Contains",
                [
                    ["text", constants.YELLOW_WARNING, "(empty)"]
                    if self.in_inv.empty
                    else ["item", self.in_slot.item.uid, self.in_slot.amount]
                ],
            ],
            [
                "Break Progress",
                [
                    [
                        "progress",
                        progress / constants.MOLD_BREAKER_CONSUME_AMOUNT,
                        "drill",
                    ]
                ],
            ],
        ]
