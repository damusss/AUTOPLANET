from src import constants
from src.shared import Slot
from src.object_data import ItemOD
from src.server.building import MovingBuildingExt
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
        return {"filter_uid": ItemOD.uid_or_none(self.filter)}

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
        data.update(self.get_config())
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
