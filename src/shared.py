import pygame

from src import constants
from src.object_data import ObjectData, TileOD, VegetationOD, BuildingOD, ItemOD


class CraftQueueItem:
    def __init__(self, item: ItemOD, amount=1, phantom=False, start_time=None):
        self.item = item
        self.amount = amount
        self.phantom = phantom
        self.start_time = start_time
        self.empty = False

    def get_client_data(self):
        return [
            self.item.uid,
            self.amount,
            self.phantom,
            pygame.time.get_ticks() - self.start_time
            if self.start_time is not None
            else None,
        ]

    @classmethod
    def from_client_data(self, data):
        return CraftQueueItem(
            ItemOD.get(data[0]),
            data[1],
            data[2],
            pygame.time.get_ticks() - data[3] if data[3] is not None else None,
        )


class Slot:
    def __init__(self, item, amount, filter_=None, i=-1):
        self.item: ItemOD = item
        self.amount = amount
        self.filter = filter_
        self.i = i

    @property
    def empty(self):
        return self.item is None or self.amount <= 0

    @property
    def full(self):
        return (not self.empty) and self.amount >= self.item.stack_size

    def set(self, item, amount, filter_=None):
        self.item = item
        self.amount = amount
        if filter_ is not None:
            self.filter = filter_

    def contains(self, item: ItemOD, amount):
        return self.item == item and self.amount >= amount

    def check_filter(self, item: ItemOD):
        if self.filter is None:
            return True
        if self.filter[0] == constants.INVENTORY_FILTER_WHITELIST:
            return item.name_id in self.filter[1]
        elif self.filter[0] == constants.INVENTORY_FILTER_CATEGORY:
            return item.category in self.filter[1]

    def get_client_data(self):
        return [
            self.item.uid if self.item is not None else None,
            self.amount,
            self.filter,
        ]


class RaycastHit:
    def __init__(
        self, chunk_key, hitbox, type_, object_data, tile_pos, tile_data, building_data
    ):
        self.chunk_key = chunk_key
        self.hitbox: pygame.FRect = hitbox
        self.type = type_
        self.object_data: TileOD | VegetationOD | BuildingOD | ObjectData = object_data
        self.tile_pos = tile_pos
        self.tile_data = tile_data
        self.building_data = building_data

    def get_client_data(self):
        return {
            "ckey": self.chunk_key,
            "hb": tuple(self.hitbox),
            "type": self.type,
            "uid": self.object_data.uid,
            "tn": self.object_data.type_name,
            "tp": self.tile_pos,
            "td": self.tile_data,
            "bd": self.building_data,
        }

    @classmethod
    def from_client_data(cls, data):
        return RaycastHit(
            data["ckey"],
            pygame.FRect(data["hb"]),
            data["type"],
            ObjectData.get_type(data["tn"]).get(data["uid"]),
            data["tp"],
            data["td"],
            data["bd"],
        )


class CraftAvailabilityStatus:
    def __init__(self, counted_items, intermediate_queue):
        if counted_items is None:
            counted_items = {}
        if intermediate_queue is None:
            intermediate_queue = []
        self.counted_items = counted_items
        self.intermediate_queue = []
        self.availability: str = None
        self.status: str = None

    def report(self, availability, status):
        self.availability = availability
        self.status = status
        return self


def craft_availability_status(
    item: ItemOD,
    count_func,
    craft_amount=1,
    parent_status: CraftAvailabilityStatus = None,
) -> CraftAvailabilityStatus:

    if parent_status:
        status = CraftAvailabilityStatus(
            parent_status.counted_items, parent_status.intermediate_queue
        )
    else:
        status = CraftAvailabilityStatus(None, None)
    if item.create_data is None:
        return status.report(
            constants.CRAFT_UNAVAILABLE, constants.CRAFT_STATUS_NOT_CRAFTABLE
        )
    substep = False
    hands = item.create_data.type == constants.CREATE_HANDS
    for req_item, amount in item.create_data.recipe:
        has_amount = count_func(req_item) - status.counted_items.get(req_item.uid, 0)
        if has_amount < amount * craft_amount:
            to_craft_amount = amount * craft_amount - has_amount
            report = craft_availability_status(
                req_item, count_func, to_craft_amount, status
            )
            if report.availability in [
                constants.CRAFT_NOT_READY,
                constants.CRAFT_UNAVAILABLE,
            ]:
                return status.report(
                    constants.CRAFT_UNAVAILABLE,
                    (
                        constants.CRAFT_STATUS_MISSING_REQUIREMENTS
                        if hands
                        else constants.CRAFT_STATUS_NO_HANDS
                    ),
                )
            status.intermediate_queue.append((req_item, to_craft_amount))
            substep = True
        else:
            status.counted_items[req_item.uid] = (
                status.counted_items.get(req_item.uid, 0) + amount * craft_amount
            )
    if not hands:
        return status.report(constants.CRAFT_NOT_READY, constants.CRAFT_STATUS_NO_HANDS)
    return status.report(
        constants.CRAFT_READY_SUBSTEP if substep else constants.CRAFT_READY, ""
    )


def get_building_topleft(center, size):
    topleft = (center - pygame.Vector2(size) / 2) + pygame.Vector2(0.5, -0.5)
    if topleft.x < 0:
        topleft.x -= 1
    if topleft.y > 0:
        topleft.y += 1
    topleft = pygame.Vector2(int(topleft.x), int(topleft.y))
    return topleft


def get_chunk_key(chunk_pos):
    return f"{int(chunk_pos[0])};{int(chunk_pos[1])}"


def get_chunk_pos(world_pos):
    world_pos = pygame.Vector2(world_pos)
    x = (world_pos.x + constants.CHUNK_SIZE / 2) / constants.CHUNK_SIZE
    y = (world_pos.y + constants.CHUNK_SIZE / 2) / constants.CHUNK_SIZE
    return pygame.Vector2(int(x if x >= 0 else x - 1), int(y if y >= 0 else y - 1))


def get_chunk_world_pos(chunk_pos):
    return pygame.Vector2(
        chunk_pos[0] * constants.CHUNK_SIZE - constants.CHUNK_SIZE / 2,
        chunk_pos[1] * constants.CHUNK_SIZE - constants.CHUNK_SIZE / 2,
    )
