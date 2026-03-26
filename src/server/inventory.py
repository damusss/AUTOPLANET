from src import constants
from src.shared import Slot
from src.object_data import ItemOD


class Inventory:
    def __init__(self):
        self.dirty = True
        self.slots = [
            Slot(None, 0, None, i)
            for i in range(constants.INVENTORY_COLS * constants.INVENTORY_ROWS + 1)
        ]
        self.slots[constants.INVENTORY_HAND_I].set(
            ItemOD.get("pickaxe"), 1, [constants.INVENTORY_FILTER_CATEGORY, ["tools"]]
        )
        # temp testing
        self.add(ItemOD.objects.bricks_platform, 10)
        self.add(ItemOD.objects.furnace, 5)

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
                self.dirty = True
                to_remove -= removed
                if slot.amount <= 0:
                    slot.item = None
                if to_remove <= 0:
                    break
        return to_remove

    def add(self, item: ItemOD, amount) -> int:
        to_add = amount
        for slot in self.slots:
            if slot.item == item and not slot.empty:
                added = min(to_add, item.stack_size - slot.amount)
                if added > 0:
                    slot.amount += added
                    self.dirty = True
                    to_add -= added
                if to_add <= 0:
                    break
        if to_add <= 0:
            return 0
        for slot in self.slots:
            if slot.empty:
                added = min(to_add, item.stack_size)
                slot.item = item
                slot.amount += added
                self.dirty = True
                to_add -= added
                if to_add <= 0:
                    break
        return to_add

    def client_action(self, action, source, dest, amount):
        source_slot: Slot = None
        dest_slot: Slot = None
        if source["container"] == "player":
            source_slot = self.slots[source["slot"]]
        if dest["container"] == "player":
            dest_slot = self.slots[dest["slot"]]
        if source_slot is dest_slot:
            return
        if action == constants.INVENTORY_ACTION_MOVE:
            if source_slot.empty:
                return
            if dest_slot.full:
                return
            if dest_slot.empty:
                if not dest_slot.check_filter(source_slot.item):
                    return
                dest_slot.item = source_slot.item
            can_remove = min(amount, source_slot.amount)
            dest_slot.amount += can_remove
            if dest_slot.amount > dest_slot.item.stack_size:
                didnt_remove = dest_slot.amount - dest_slot.item.stack_size
                dest_slot.amount = dest_slot.item.stack_size
                can_remove -= didnt_remove
            source_slot.amount -= can_remove
        elif action == constants.INVENTORY_ACTION_SWAP:
            if source_slot.empty or dest_slot.empty:
                return
            if not dest_slot.check_filter(source_slot.item):
                return
            if not source_slot.check_filter(dest_slot.item):
                return
            source_slot.item, dest_slot.item = dest_slot.item, source_slot.item
            source_slot.amount, dest_slot.amount = dest_slot.amount, source_slot.amount
        self.dirty = True

    def get_client_data(self):
        return [slot.get_client_data() for slot in self.slots]
