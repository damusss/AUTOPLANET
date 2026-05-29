from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.shared import Slot
from src.object_data import ItemOD, TileOD
from src.server.building import BuildingExt, MovingBuildingExt
from src.server.inventory import BuildingInventory


class Bot(MovingBuildingExt, name_id="bot"):
    def init(self):
        self.slot = Slot(None, 0, None, 0)
        self.inventory = BuildingInventory(self, self.slot)
        self.upgrade_slot = Slot(
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

    def get_config(self):
        return {"filter_uid": None if self.filter is None else self.filter.uid}

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

    def get_extra_raycast_data(self):
        sections = [
            [
                "Contains",
                [
                    ["text", constants.UI_INFO_DESCR_COL, "(empty)"]
                    if self.inventory.empty
                    else [
                        "item",
                        self.slot.item.uid,
                        self.slot.amount,
                    ],
                    [
                        "text",
                        constants.GREEN_GOOD
                        if self.building.moving
                        else constants.YELLOW_WARNING,
                        "Moving" if self.building.moving else "Idle",
                    ],
                ],
            ]
        ]
        if self.filter is not None:
            sections.append(["Filter", [["item", self.filter.uid, None]]])
        if not self.upgrade_slot.empty:
            sections.append(
                [
                    "Upgrade",
                    [
                        [
                            "item",
                            self.upgrade_slot.item.uid,
                            self.upgrade_slot.amount,
                        ]
                    ],
                ]
            )
        return sections


class Lamp(BuildingExt, name_id="lamp"):
    def on_energy_awake(self):
        self.building.change_state("on")

    def on_energy_sleep(self):
        self.building.change_state("off")


class Storage(BuildingExt, name_id="storage"):
    def init(self):
        self.inventory = BuildingInventory(self)
        for i in range(constants.INVENTORY_ROWS * constants.INVENTORY_COLS):
            self.inventory.add_slot(Slot(None, 0, None, i))
        self.inventories["in"] = self.inventory
        self.inventories["out"] = self.inventory


class Hopper(BuildingExt, name_id="hopper"):
    def init(self):
        self.slot = Slot(None, 0, None, 0)
        self.inventory = BuildingInventory(self, self.slot)
        self.inventories["in"] = self.inventory
        self.inventories["out"] = self.inventory

    def get_extra_raycast_data(self):
        return [
            [
                "Contains",
                [
                    ["text", constants.UI_INFO_DESCR_COL, "(empty)"]
                    if self.inventory.empty
                    else [
                        "item",
                        self.slot.item.uid,
                        self.slot.amount,
                    ]
                ],
            ]
        ]


class Miner(BuildingExt, name_id="miner"):
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
        self.work_start_time = god.world.get_ticks()
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

    def get_extra_raycast_data(self):
        mining = []
        space = True
        for tile_data in self.tile_datas:
            drop = TileOD.get(tile_data[0]).item_drop[0][0]
            if drop not in mining:
                mining.append(drop)
                if not self.out_inv.has_space(drop, 1, ignore_filters=True):
                    space = False
        slots = []
        for drop in mining:
            slots.append(["item", drop.uid, self.out_inv.count(drop)])
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
        return {"recipe_uid": None if self.recipe is None else self.recipe.uid}

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
        data["recipe_uid"] = self.recipe.uid if self.recipe is not None else None
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


class Furnace(BuildingExt, name_id="furnace"):
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
