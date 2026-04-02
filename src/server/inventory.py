import typing

from src import shared
from src import constants
from src.server import god
from src.object_data import ItemOD

if typing.TYPE_CHECKING:
    from src.server.player import Player
    from src.server.building import BuildingExt


class CommonInventory:
    slots: list[shared.Slot]

    @property
    def empty(self):
        return all((slot.empty for slot in self.slots))

    def has_space(self, item: ItemOD, amount, ignore_filters=True):
        to_add = amount
        for slot in self.slots:
            if slot.empty and (ignore_filters or slot.check_filter(item)):
                added = min(to_add, item.stack_size)
                to_add -= added
                if to_add <= 0:
                    break
            elif slot.item == item:
                added = min(to_add, item.stack_size - slot.amount)
                to_add -= added
                if to_add <= 0:
                    break
        return to_add <= 0

    def set_dirty(self): ...

    def has(self, item: ItemOD, amount):
        return self.count(item) >= amount

    def count(self, item: ItemOD):
        count = 0
        for slot in self.slots:
            if slot.item == item:
                count += slot.amount
        return count

    def remove(self, item: ItemOD, amount):
        to_remove = amount
        for slot in self.slots:
            if slot.item == item:
                removed = min(to_remove, slot.amount)
                slot.amount -= removed
                self.set_dirty()
                to_remove -= removed
                if slot.amount <= 0:
                    slot.item = None
                if to_remove <= 0:
                    break
        return to_remove

    def add(self, item: ItemOD, amount, ignore_filters=False) -> int:
        to_add = amount
        for slot in self.slots:
            if slot.item == item and not slot.empty:
                added = min(to_add, item.stack_size - slot.amount)
                if added > 0:
                    slot.amount += added
                    self.set_dirty()
                    to_add -= added
                if to_add <= 0:
                    break
        if to_add <= 0:
            return 0
        for slot in self.slots:
            if slot.empty and (ignore_filters or slot.check_filter(item)):
                added = min(to_add, item.stack_size)
                slot.item = item
                slot.amount += added
                self.set_dirty()
                to_add -= added
                if to_add <= 0:
                    break
        return to_add

    def get_client_data(self):
        return [slot.get_client_data() for slot in self.slots]


class BuildingInventory(CommonInventory):
    def __init__(self, bext, *slots):
        self.bext: "BuildingExt" = bext
        self.slots: list[shared.Slot] = []
        for slot in slots:
            self.add_slot(slot)

    @property
    def slot(self) -> shared.Slot:
        return self.slots[0]

    def set_dirty(self):
        self.bext.on_inventory_dirty()

    def add_slot(self, slot):
        self.slots.append(slot)


class Inventory(CommonInventory):
    def __init__(self, player):
        self.player: "Player" = player
        self.dirty = True
        self.slots = [
            shared.Slot(None, 0, None, i)
            for i in range(constants.INVENTORY_COLS * constants.INVENTORY_ROWS + 1)
        ]
        self.slots[constants.INVENTORY_HAND_I].set(
            ItemOD.objects.pickaxe, 1, [constants.INVENTORY_FILTER_CATEGORY, ["tools"]]
        )
        # temp testing
        self.add(ItemOD.objects.storage, 10)
        self.add(ItemOD.objects.furnace, 5)
        self.add(ItemOD.objects.miner, 5)
        self.add(ItemOD.objects.energy_plant, 3)
        self.add(ItemOD.objects.energy_transmitter, 300)
        self.add(ItemOD.objects.lamp, 20)
        self.add(ItemOD.objects.iron, constants.DEFAULT_STACK_SIZE)
        self.add(ItemOD.objects.iron_ore, constants.DEFAULT_STACK_SIZE)
        self.add(ItemOD.objects.bot, 100)

    def set_dirty(self):
        self.dirty = True

    def client_action(self, action, source, dest, amount):
        other_source_inventory: CommonInventory | None = None
        other_dest_inventory: CommonInventory | None = None
        concentrate_source: list[shared.Slot] = None
        source_slot: shared.Slot = None
        dest_slot: shared.Slot = None
        mult = 1
        if source["cont"] == "player":
            if source["slot"] is not None:
                try:
                    source_slot = self.slots[source["slot"]]
                except IndexError:
                    source_slot = None
            else:
                source_slot = None
                concentrate_source = self.slots
        elif " " in source["cont"]:
            building_id, inventory_name = source["cont"].split(" ")
            if building_id in god.world.buildings:
                building = god.world.buildings[building_id]
                inventory = building.ext.inventories.get(inventory_name, None)
                if inventory is not None:
                    other_source_inventory = inventory
                    if source["slot"] is not None:
                        try:
                            source_slot = other_source_inventory.slots[source["slot"]]
                        except IndexError:
                            source_slot = None
                    else:
                        source_slot = None
                        concentrate_source = other_source_inventory.slots
        if dest["cont"] == "player":
            try:
                dest_slot = self.slots[dest["slot"]]
            except IndexError:
                dest_slot = None
        elif dest["cont"] in ["left", "right"]:
            if dest["cont"] == "left":
                mult = -1
        elif " " in dest["cont"]:
            building_id, inventory_name = dest["cont"].split(" ")
            if building_id in god.world.buildings:
                building = god.world.buildings[building_id]
                inventory = building.ext.inventories.get(inventory_name, None)
                if inventory is not None:
                    other_dest_inventory = inventory
                    try:
                        dest_slot = other_dest_inventory.slots[dest["slot"]]
                    except IndexError:
                        dest_slot = None
        if source_slot is dest_slot:
            return
        if action == constants.INVENTORY_ACTION_MOVE:
            if source_slot is None or dest_slot is None:
                return
            if source_slot.empty:
                return
            if dest_slot.full:
                return
            if not dest_slot.check_filter(source_slot.item):
                return
            if dest_slot.empty:
                dest_slot.item = source_slot.item
            can_remove = min(amount, source_slot.amount)
            dest_slot.amount += can_remove
            if dest_slot.amount > dest_slot.item.stack_size:
                didnt_remove = dest_slot.amount - dest_slot.item.stack_size
                dest_slot.amount = dest_slot.item.stack_size
                can_remove -= didnt_remove
            source_slot.amount -= can_remove
        elif action == constants.INVENTORY_ACTION_SWAP:
            if source_slot is None or dest_slot is None:
                return
            if source_slot.empty or dest_slot.empty:
                return
            if not dest_slot.check_filter(source_slot.item):
                return
            if not source_slot.check_filter(dest_slot.item):
                return
            source_slot.item, dest_slot.item = dest_slot.item, source_slot.item
            source_slot.amount, dest_slot.amount = dest_slot.amount, source_slot.amount
        elif action == constants.INVENTORY_ACTION_CONCENTRATE:
            if dest_slot.empty:
                return
            available = dest_slot.item.stack_size - dest_slot.amount
            concentrated = 0
            if available <= 0:
                return
            for slot in sorted(concentrate_source, key=lambda s: s.amount):
                if available <= 0:
                    break
                if slot is dest_slot:
                    continue
                if not slot.empty and slot.item == dest_slot.item:
                    take_amount = min(available, slot.amount)
                    slot.amount -= take_amount
                    available -= take_amount
                    concentrated += take_amount
            dest_slot.amount += concentrated
        elif action == constants.INVENTORY_ACTION_DROP:
            if source_slot.empty:
                return
            amount = min(amount, source_slot.amount)
            source_slot.amount -= amount
            god.world.drop(
                shared.get_drop_random_pos(self.player.hitbox.move(mult, -1)),
                source_slot.item,
                amount,
            )
        self.set_dirty()
        if other_source_inventory is not None:
            other_source_inventory.set_dirty()
        if other_dest_inventory is not None:
            other_dest_inventory.set_dirty()
