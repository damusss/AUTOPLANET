from src import constants
from src.shared import Slot
from src.object_data import ItemOD
from src.server.building import BuildingExt
from src.server.inventory import BuildingInventory


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
                    ]
                ],
            ]
        ]
        if self.filter is not None:
            sections.append(["Filter", [["item", self.filter.uid, None]]])
        return sections
