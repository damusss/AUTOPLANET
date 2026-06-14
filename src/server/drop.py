import math
import random
import typing

import pygame

from src import shared
from src import constants
from src.server import god
from src.object_data import ItemOD

if typing.TYPE_CHECKING:
    from src.server.chunk import Chunk


class Drop:
    def __init__(self, pos, chunk, item, amount):
        self.pos = pygame.Vector2(pos)
        self.vel = 0
        self.chunk: "Chunk" = chunk
        self.item: ItemOD = item
        self.amount = amount
        self.last_raycast = god.world.get_ticks()
        self.anim_offset = random.uniform(0, math.tau)

    @property
    def hitbox(self):
        return pygame.FRect(0, 0, constants.DROP_SIZE, constants.DROP_SIZE).move_to(
            center=self.pos
        )

    def destroy(self):
        try:
            self.chunk.drops.remove(self)
        except ValueError:
            ...

    def get_client_data(self):
        return [
            round(self.pos.x, constants.DIGIT_PRECISION),
            round(self.pos.y, constants.DIGIT_PRECISION),
            self.item.uid,
            round(self.anim_offset, constants.DIGIT_PRECISION),
        ]

    def frame(self):
        if god.world.get_ticks() - self.last_raycast >= 100:
            chunk_key = shared.get_chunk_key(shared.get_chunk_pos(self.pos))
            if chunk_key in god.world.chunks:
                if chunk_key != self.chunk.chunk_key:
                    try:
                        self.chunk.drops.remove(self)
                    except ValueError:
                        ...
                    new = god.world.chunks[chunk_key]
                    new.drops.append(self)
                    self.chunk = new
        self.vel += constants.GRAVITY * god.dt
        self.pos.y += self.vel * god.dt
        hitbox = self.hitbox
        colliding = god.world.get_chunks_collding_rect(hitbox, 0.05)
        self.collisions(colliding, hitbox)

    def collisions(self, chunks: list["Chunk"], hitbox):
        prev_y = hitbox.y
        for chunk in chunks:
            for rect in chunk.tile_hitboxes + chunk.building_floor_hitboxes:
                if rect.colliderect(hitbox):
                    if rect.centery > hitbox.bottom > rect.top:
                        hitbox.bottom = rect.top
                        self.vel = 0
                        self.pos.y += hitbox.y - prev_y
                        break
