import typing

import pygame

from src import constants
from src.object_data import ObjectData, TileOD, VegetationOD, BuildingOD, ItemOD


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

    def contains(self, item: ItemOD, amount):
        return self.item == item and self.amount >= amount

    def check_filter(self, item: ItemOD):
        if self.filter is None:
            return True
        if self.filter[0] == constants.INVENTORY_FILTER_WHITELIST:
            return item.name_id in self.filter[1]
        elif self.filter[0] == constants.INVENTORY_FILTER_CATEGORY:
            return item.category == self.filter[1]

    def get_client_data(self):
        return [
            self.item.uid if self.item is not None else None,
            self.amount,
            self.filter,
        ]


class RaycastHit:
    def __init__(self, chunk_key, hitbox, type_, object_data, tile_pos):
        self.chunk_key = chunk_key
        self.hitbox: pygame.FRect = hitbox
        self.type = type_
        self.object_data: TileOD | VegetationOD | BuildingOD | ObjectData = object_data
        self.tile_pos = tile_pos

    def get_client_data(self):
        return {
            "chunk_key": self.chunk_key,
            "hitbox": tuple(self.hitbox),
            "type": self.type,
            "object_uid": self.object_data.uid,
            "object_type_name": self.object_data.type_name,
            "tile_pos": self.tile_pos,
        }

    @classmethod
    def from_client_data(cls, data):
        return RaycastHit(
            data["chunk_key"],
            pygame.FRect(data["hitbox"]),
            data["type"],
            ObjectData.get_type(data["object_type_name"]).get(data["object_uid"]),
            data["tile_pos"],
        )


def get_chunk_key(chunk_pos):
    return f"{int(chunk_pos[0])};{int(chunk_pos[1])}"


def get_chunk_pos(world_pos):
    world_pos = pygame.Vector2(world_pos)
    x = (world_pos.x + constants.CHUNK_SIZE / 2) / constants.CHUNK_SIZE
    y = (world_pos.y + constants.CHUNK_SIZE / 2) / constants.CHUNK_SIZE
    return pygame.Vector2(int(x if x >= 0 else x - 1), int(y if y >= 0 else y - 1))
