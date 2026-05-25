import math
import random

import pygame

from src import constants
from src.object_data import ObjectData, TileOD, VegetationOD, BuildingOD, ItemOD

time_get_ticks = pygame.time.get_ticks


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
            eval_delta(self.start_time) if self.start_time is not None else None,
        ]

    @classmethod
    def from_client_data(self, data):
        return CraftQueueItem(
            ItemOD.get(data[0]),
            data[1],
            data[2],
            eval_delta(data[3]) if data[3] is not None else None,
        )


class Slot:
    hitbox: pygame.Rect

    def __init__(self, item, amount, filter_=None, i=-1, cont: str | None = None):
        self.item: ItemOD = item
        self.amount = amount
        self.filter = filter_
        self.i = i
        if cont:
            self.cont = cont

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

    def contains_any(self, items: list[ItemOD], amount):
        return any((self.contains(item, amount) for item in items))

    def check_filter(self, item: ItemOD):
        if self.filter is None:
            return True
        if self.filter[0] == constants.INVENTORY_FILTER_WHITELIST:
            return item.name_id in self.filter[1]
        elif self.filter[0] == constants.INVENTORY_FILTER_CATEGORY:
            return item.category in self.filter[1]
        elif self.filter[0] == constants.INVENTORY_FILTER_READONLY:
            return False

    def get_client_data(self):
        return [
            self.item.uid if self.item is not None else None,
            self.amount,
            self.filter,
        ]


class RaycastHit:
    def __init__(
        self, chunk_key, hitbox, type_, object_data, tile_pos, tile_data, data
    ):
        self.chunk_key = chunk_key
        self.hitbox: pygame.FRect = hitbox
        self.type: int = type_
        self.object_data: TileOD | VegetationOD | BuildingOD | ObjectData = object_data
        self.tile_pos: tuple[int, int] | None = tile_pos
        self.tile_data: tuple | None = tile_data
        self.data = data

    def get_client_data(self):
        return {
            "ckey": self.chunk_key,
            "hb": tuple(self.hitbox),
            "type": self.type,
            "uid": self.object_data.uid,
            "tn": self.object_data.type_name,
            "tp": self.tile_pos,
            "td": self.tile_data,
            "d": self.data,
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
            data["d"],
        )


class Mail:
    def __init__(self, type, client_id, **data):
        self.type = type[0]
        self.client_id = client_id
        self.data: dict = data
        self.valid = all((field in self.data for field in type[1]))
        if not self.valid:
            log(
                f"[ERR] Invalid mail for type {self.type}. Missing fields: {[field for field in type[1] if field not in self.data]}"
            )
        for attr, val in self.data.items():
            setattr(self, attr, val)

    def compare(self, type):
        return self.type == type[0]

    def missing_fields(self, *required_fields, cont_data=None):
        data = cont_data if cont_data is not None else self.data
        result = any((field not in self.data for field in required_fields))
        if result:
            cont_str = ""
            if cont_data is not None:
                cont_str = f" in data={cont_data}"
            log(
                f"[ERR] Invalid mail for type {self.type}. Missing fields: {[field for field in required_fields if field not in data]}{cont_str}"
            )
        return result


class CraftAvailabilityStatus:
    def __init__(self, counted_items, intermediate_queue):
        if counted_items is None:
            counted_items = {}
        if intermediate_queue is None:
            intermediate_queue = []
        self.counted_items = counted_items
        self.intermediate_queue = intermediate_queue
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


def rect_collide_circle(rect: pygame.FRect, center, radius):
    dx = max(abs(center[0] - rect.centerx) - rect.w / 2, 0)
    dy = max(abs(center[1] - rect.centery) - rect.h / 2, 0)
    distance2 = dx * dx + dy * dy
    return distance2 <= radius**2


def get_drop_random_pos(hitbox: pygame.FRect):
    return pygame.Vector2(
        random.uniform(
            hitbox.left + constants.DROP_SIZE / 2,
            hitbox.right - constants.DROP_SIZE / 2,
        ),
        random.uniform(
            hitbox.top + constants.DROP_SIZE / 2,
            hitbox.bottom - constants.DROP_SIZE / 2,
        ),
    )


def get_trajectory_chunks(a: pygame.Vector2, b: pygame.Vector2) -> set[str]:
    p = pygame.Vector2(a)
    chunks = set()
    direction = b - a
    if direction.magnitude() != 0:
        direction = (b - a).normalize()
    for _ in range(int(a.distance_to(b) / constants.TRAJECTORY_STEP_SIZE) + 1):
        cpos = get_chunk_pos(p)
        ckey = get_chunk_key(cpos)
        chunks.add(ckey)
        p += direction * constants.TRAJECTORY_STEP_SIZE
    return chunks


def get_chunk_keys_colliding_circle(center, radius, offset=0):
    center = pygame.Vector2(center)
    north = pygame.Vector2(center.x, center.y - radius - offset)
    south = pygame.Vector2(center.x, center.y + radius + offset)
    east = pygame.Vector2(center.x - radius - offset, center.y)
    west = pygame.Vector2(center.x + radius + offset, center.y)
    north_cpos = get_chunk_pos(north)
    south_cpos = get_chunk_pos(south)
    east_cpos = get_chunk_pos(east)
    west_cpos = get_chunk_pos(west)
    colliding = set()
    for cx in range(int(east_cpos.x), int(west_cpos.x) + 1):
        for cy in range(int(north_cpos.y), int(south_cpos.y) + 1):
            hitbox = pygame.FRect(
                get_chunk_world_pos((cx, cy)),
                (constants.CHUNK_SIZE, constants.CHUNK_SIZE),
            )
            if rect_collide_circle(hitbox, center, radius):
                key = get_chunk_key((cx, cy))
                colliding.add(key)
    return colliding


def mult_rect(rect: pygame.FRect, mult):
    center = rect.center
    rect.w *= mult
    rect.h *= mult
    rect.center = center
    return rect


def eval_delta(time):
    return time_get_ticks() - time


def get_building_id():
    return "".join(
        [
            random.choice(constants.BUILDING_ID_ALPHABET)
            for _ in range(constants.BUILDING_ID_LEN)
        ]
    )


def get_float_anim(height, time_mult, offset):
    return ((math.sin(time_get_ticks() * time_mult + offset)) + 1) / 2 * height


def other_kind(name, strip=False):
    if name == "in":
        return "out"
    if name == "input":
        return "out" if strip else "output"
    if name == "out":
        return "in"
    if name == "output":
        return "in" if strip else "input"


def log(*args, **kwargs):
    print(*args, **kwargs)
