import typing

import pygame

from src import shared
from src import mailbox
from src import constants
from src.object_data import BuildingOD

if typing.TYPE_CHECKING:
    from src.server.chunk import Chunk


class Building:
    def __init__(self, id_: str, building_od: BuildingOD, topleft, chunk):
        self.id = id_
        self.building_od = building_od
        self.hitbox = pygame.FRect(topleft, building_od.size)
        self.chunk: "Chunk" = chunk
        self.bordering_chunks: list["Chunk"] = []
        self.state = self.building_od.states["default"].name

    def get_raycast_data(self):
        return [self.id, self.state]

    def get_client_data(self):
        return [
            self.id,
            self.building_od.uid,
            int(self.hitbox.x),
            int(self.hitbox.y),
            self.state,
        ]
