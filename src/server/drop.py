import typing

import pygame

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
        self.last_raycast = pygame.time.get_ticks()

    @property
    def hitbox(self):
        return pygame.FRect(0, 0, constants.DROP_SIZE, constants.DROP_SIZE).move_to(
            center=self.pos
        )

    def destroy(self):
        self.chunk.drops.remove(self)

    def get_client_data(self):
        return [
            round(self.pos.x, constants.DIGIT_PRECISION),
            round(self.pos.y, constants.DIGIT_PRECISION),
            self.item.uid,
            self.amount,
        ]

    def frame(self):
        if pygame.time.get_ticks() - self.last_raycast >= 100:
            raycast = god.world.raycast(self.pos, constants.RAYCASTFLAG_CHUNK)
            if raycast:
                if raycast.chunk_key != self.chunk.chunk_key:
                    self.chunk.drops.remove(self)
                    new = god.world.chunks[raycast.chunk_key]
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
            for rect in chunk.tile_hitboxes:
                if rect.colliderect(hitbox):
                    if hitbox.bottom < rect.centery and hitbox.bottom > rect.top:
                        hitbox.bottom = rect.top
                        self.vel = 0
                        self.pos.y += hitbox.y - prev_y
                        break
