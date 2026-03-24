import random

import pygame

from src import shared
from src import mailbox
from src import constants
from src.server import god
from src.timerc import timerc
from src.object_data import TileOD
from src.server.drop import Drop
from src.server.chunk import Chunk
from src.server.player import Player


class World:
    def __init__(self):
        god.world = self
        self.dt = 0
        self.seed = random.randint(0, int(10e6))
        self.seed_caves = random.randint(0, int(10e6))
        self.players: dict[int, Player] = {}
        self.clock = pygame.Clock()
        self.chunks: dict[str, Chunk] = {}

    def player_connect(self, client):
        player = Player(client)
        self.players[client.id] = player

    def player_disconnect(self, client):
        player = self.players[client.id]
        for chunk in player.client_loaded_chunks:
            self.chunks[chunk].loaded_client_players.remove(player)
        self.players.pop(client.id)

    def load_or_get_chunk(self, key, pos):
        if key in self.chunks:
            return self.chunks[key]
        chunk = Chunk(key, pos)
        self.chunks[key] = chunk
        return chunk

    def player_drops_collisions(
        self, player: Player, drops: list[Drop], update, drops_data
    ):
        hitbox = player.hitbox
        for drop in list(drops):
            if drop.hitbox.colliderect(hitbox):
                not_added = player.inventory.add(drop.item, drop.amount)
                if not_added == 0:
                    drop.destroy()
                else:
                    drop.amount = not_added
            if update:
                drop.frame()
            drops_data.append(drop.get_client_data())

    def refresh_player_chunks(self, player: Player, checked_for_drops: set):
        visible_chunks = set()
        drops_data = []
        for x_offset in range(
            int(-constants.RENDER_DISTANCE[0] / 2),
            int(constants.RENDER_DISTANCE[0] / 2) + 1,
        ):
            for y_offset in range(
                int(-constants.RENDER_DISTANCE[1] / 2),
                int(constants.RENDER_DISTANCE[1] / 2),
            ):
                world_pos = pygame.Vector2(
                    player.pos.x + x_offset * constants.CHUNK_SIZE,
                    player.pos.y + y_offset * constants.CHUNK_SIZE,
                )
                chunk_pos = shared.get_chunk_pos(world_pos)
                key = shared.get_chunk_key(chunk_pos)
                chunk = self.load_or_get_chunk(key, chunk_pos)
                self.player_drops_collisions(
                    player, chunk.drops, key not in checked_for_drops, drops_data
                )
                if key not in checked_for_drops:
                    checked_for_drops.add(key)
                visible_chunks.add(key)
                if key not in player.client_loaded_chunks:
                    player.client_chunks_queue.append(key)
                    player.client_loaded_chunks.add(key)
                    chunk.loaded_client_players.append(player)
        if len(player.client_chunks_queue) > 0:
            chunk = self.chunks[player.client_chunks_queue.popleft()]
            player.client.conn.mail(
                mailbox.MAIL_CHUNK_LOAD,
                chunks={chunk.chunk_key: chunk.get_client_data()},
                refresh=False,
            )
        diff = player.client_loaded_chunks.difference(visible_chunks)
        if diff:
            for ckey in diff:
                self.chunks[ckey].loaded_client_players.remove(player)
                player.client_loaded_chunks.remove(ckey)
            player.client.conn.mail(mailbox.MAIL_CHUNK_UNLOAD, chunk_keys=list(diff))
        return drops_data

    def get_chunks_collding_rect(
        self, rect: pygame.FRec, bottom_offset=0, side_offset=0
    ) -> list[Chunk]:
        colliding = []
        for point in (
            rect.topleft,
            rect.topright,
            pygame.Vector2(rect.bottomleft)
            + pygame.Vector2(-side_offset, bottom_offset),
            pygame.Vector2(rect.bottomright)
            + pygame.Vector2(side_offset, bottom_offset),
        ):
            cpos = shared.get_chunk_pos(point)
            ckey = shared.get_chunk_key(cpos)
            if ckey in self.chunks and ckey not in colliding:
                colliding.append(self.chunks[ckey])
        return colliding

    def drop(self, pos, item, amount):
        raycast = self.raycast(pos, constants.RAYCASTFLAG_CHUNK)
        if raycast is None:
            return
        chunk = self.chunks[raycast.chunk_key]
        drop = Drop(pos, chunk, item, amount)
        chunk.drops.append(drop)

    def break_raycast(self, raycast: shared.RaycastHit):
        chunk = self.chunks[raycast.chunk_key]
        if raycast.type == constants.RAYCAST_TILE:
            tile_data = chunk.get_tile(raycast.tile_pos)
            if tile_data[1] == 0:
                return
            tile_data[1] = 0
            if raycast.tile_pos in chunk.tile_hitboxes_table:
                hitbox = chunk.tile_hitboxes_table.pop(raycast.tile_pos)
                chunk.tile_hitboxes.remove(hitbox)

                tile_od = TileOD.get(tile_data[0])
                for drop in tile_od.item_drop:
                    self.drop(
                        (
                            random.uniform(
                                hitbox.left + constants.DROP_SIZE / 2,
                                hitbox.right - constants.DROP_SIZE / 2,
                            ),
                            random.uniform(
                                hitbox.top + constants.DROP_SIZE / 2,
                                hitbox.bottom - constants.DROP_SIZE / 2,
                            ),
                        ),
                        drop[0],
                        drop[1],
                    )

            for player in chunk.loaded_client_players:
                player.client.conn.mail(
                    mailbox.MAIL_CHUNK_LOAD,
                    chunks={chunk.chunk_key: chunk.get_client_data()},
                    refresh=True,
                )

    def raycast(self, pos, flag=constants.RAYCASTFLAG_INFO):
        pos = pygame.Vector2(pos)
        chunk_pos = shared.get_chunk_pos(pos)
        chunk_key = shared.get_chunk_key(chunk_pos)
        if chunk_key not in self.chunks:
            return None
        if flag == constants.RAYCASTFLAG_CHUNK:
            return shared.RaycastHit(chunk_key, None, constants.RAYCAST_EMPTY, None, None)
        chunk = self.chunks[chunk_key]
        tile_pos = (
            int(pos.x - chunk.world_topleft.x),
            int(pos.y - chunk.world_topleft.y),
        )
        if tile_pos in chunk.tile_hitboxes_table or flag==constants.RAYCASTFLAG_ALL:
            tile_data = chunk.get_tile(tile_pos)
            return shared.RaycastHit(
                chunk_key,
                chunk.tile_hitboxes_table.get(tile_pos, None),
                constants.RAYCAST_TILE,
                TileOD.get(tile_data[0]),
                tile_pos,
            )

    def frame(self):
        self.dt = self.clock.tick_busy_loop(constants.SERVER_FPS) / 1000
        god.dt = self.dt
        god.dt = pygame.math.clamp(god.dt, 0, 1 / 60)
        checked_chunks_for_drops = set()
        for player in self.players.values():
            drops_data = self.refresh_player_chunks(player, checked_chunks_for_drops)
            hitbox = player.hitbox
            colliding = self.get_chunks_collding_rect(hitbox, 0.1, 0.2)
            rects = sum([chunk.tile_hitboxes for chunk in colliding], start=[])
            player.raycast = self.raycast(player.client_mouse_pos)
            player.frame(rects, drops_data)
        timerc.frame()
