import random

import pygame

from src import shared
from src import mailbox
from src import constants
from src.server import god
from src.timerc import timerc
from src.object_data import TileOD, BuildingOD
from src.server.drop import Drop
from src.server.chunk import Chunk
from src.server.player import Player
from src.server.building import Building


class World:
    def __init__(self):
        god.world = self
        self.dt = 0
        self.seed = random.randint(0, int(10e6))
        self.seed_caves = random.randint(0, int(10e6))
        self.players: dict[int, Player] = {}
        self.clock = pygame.Clock()
        self.chunks: dict[str, Chunk] = {}
        self.buildings: dict[str, Building] = {}

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

    def refresh_chunk(self, chunk: Chunk):
        for player in chunk.loaded_client_players:
            player.client.conn.mail(
                mailbox.MAIL_CHUNK_LOAD,
                chunks={chunk.chunk_key: chunk.get_client_data()},
                refresh=True,
            )

    def break_building(self, building: Building):
        building.chunk.building_ids.remove(building.id)
        if building.building_od.floor:
            building.chunk.building_floor_hitboxes.remove(building.hitbox)
        for chunk in building.bordering_chunks + [building.chunk]:
            for tile_pos, bid in list(chunk.tile_hitboxes_table.items()):
                if bid == building.id:
                    chunk.tile_hitboxes_table.pop(tile_pos)
        self.buildings.pop(building.id)
        self.drop(building.hitbox.center, building.building_od.item, 1)
        self.refresh_chunk(building.chunk)

    def break_raycast(self, raycast: shared.RaycastHit):
        chunk = self.chunks[raycast.chunk_key]
        if raycast.type == constants.RAYCAST_TILE:
            tile_data = chunk.get_tile(raycast.tile_pos)
            if tile_data[1] == 0:
                return
            tile_data[1] = 0
            if len(tile_data) == 4 and tile_data[3] == constants.TILE_PLACED:
                chunk.tiles_mat[chunk.get_tile_index(raycast.tile_pos)] = None
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
            self.refresh_chunk(chunk)
        elif raycast.type == constants.RAYCAST_BUILDING:
            if raycast.building_data[0] in self.buildings:
                self.break_building(self.buildings[raycast.building_data[0]])

    def air_valid_for_building(
        self, building: BuildingOD, ray: shared.RaycastHit, topleft: pygame.Vector2
    ):
        # check altitude
        if building.altitude_range is not None and topleft.y not in range(
            building.altitude_range[0], building.altitude_range[1]
        ):
            return constants.BUILDING_STATUS_WRONG_ALTITUDE
        # a non static building that can be placed on air doesn't care if it's obstructed
        if building.air and not building.static:
            return constants.BUILDING_STATUS_AVAILABLE
        if ray is not None:
            if ray.hitbox is not None:
                # if there's a hitbox it's obstructed unless it's a non-static building
                if ray.object_data.type_name != "Building" or ray.object_data.static:
                    return constants.BUILDING_STATUS_OBSTRUCTED
            # if it's a platform and there's no background tile there could be a floor saving it
            if building.restore_tile is not None or building.replace_tile:
                if ray.tile_data is None:
                    return constants.BUILDING_STATUS_COULD_BE_MISSING_FLOOR_OR_TILE
        # no ray/hitbox = air
        return constants.BUILDING_STATUS_AVAILABLE

    def floor_valid_for_building(self, building: BuildingOD, ray: shared.RaycastHit):
        # a building that can be placed on air doesn't concern itself with the floor
        if building.air:
            return constants.BUILDING_STATUS_AVAILABLE
        if ray is None or ray.hitbox is None:
            # if it's a platform there could be a background tile saving it
            if building.restore_tile is not None or building.replace_tile:
                return constants.BUILDING_STATUS_COULD_BE_MISSING_FLOOR_OR_TILE
            # if there's no hitbox below the floor is missing
            return constants.BUILDING_STATUS_MISSING_FLOOR
        found_valid_floor = (
            len(building.floor_whitelist) <= 0
        )  # true if no requirements
        for floor_req in building.floor_whitelist:
            if ray.object_data == floor_req:
                found_valid_floor = True
                break
        # if the floor wasn't in the whitelist it cannot be placed
        if not found_valid_floor:
            return constants.BUILDING_STATUS_WRONG_FLOOR
        return constants.BUILDING_STATUS_AVAILABLE

    def can_place_building(self, building_od: BuildingOD, pos, player: Player):
        if player.pos.distance_to(pos) > constants.PLAYER_REACH_RADIUS:
            return constants.BUILDING_STATUS_TOO_FAR
        topleft = shared.get_building_topleft(pos, building_od.size)
        ret_valid_f = constants.BUILDING_STATUS_AVAILABLE
        do_return_f = False
        for x in range(building_od.size[0]):
            floor_ray = self.raycast(
                (topleft.x + x + 0.5, topleft.y + building_od.size[1] + 0.5),
                constants.RAYCASTFLAG_COLLIDER,
            )
            valid_f = self.floor_valid_for_building(building_od, floor_ray)
            # if there is no floor but it's a platform let's check if there's a background tile
            if valid_f not in [
                constants.BUILDING_STATUS_AVAILABLE,
                constants.BUILDING_STATUS_COULD_BE_MISSING_FLOOR_OR_TILE,
            ]:
                if valid_f == (
                    constants.BUILDING_STATUS_WRONG_FLOOR
                    and ret_valid_f == constants.BUILDING_STATUS_MISSING_FLOOR
                ) or (
                    valid_f == constants.BUILDING_STATUS_MISSING_FLOOR
                    and ret_valid_f == constants.BUILDING_STATUS_WRONG_FLOOR
                ):
                    ret_valid_f = constants.BUILDING_STATUS_WRONG_AND_MISSING_FLOOR
                if (
                    valid_f
                    not in [
                        constants.BUILDING_STATUS_WRONG_FLOOR,
                        constants.BUILDING_STATUS_MISSING_FLOOR,
                    ]
                    or ret_valid_f != constants.BUILDING_STATUS_WRONG_AND_MISSING_FLOOR
                ):
                    ret_valid_f = valid_f
                do_return_f = True
            for y in range(building_od.size[1]):
                body_ray = self.raycast(
                    topleft + (x + 0.5, y + 0.5), constants.RAYCASTFLAG_ALL
                )
                valid_b = self.air_valid_for_building(building_od, body_ray, topleft)
                if valid_b != constants.BUILDING_STATUS_AVAILABLE:
                    # if there's no floor and no background tile let's output the proper error
                    if (
                        valid_b
                        == constants.BUILDING_STATUS_COULD_BE_MISSING_FLOOR_OR_TILE
                        and valid_f != constants.BUILDING_STATUS_AVAILABLE
                    ):
                        return constants.BUILDING_STATUS_MISSING_FLOOR_AND_TILE
                    # if the error is not about floor/background tile let it be an error, otherwise let it succeed
                    elif (
                        valid_b
                        != constants.BUILDING_STATUS_COULD_BE_MISSING_FLOOR_OR_TILE
                    ):
                        return valid_b
        if do_return_f:
            return ret_valid_f
        return constants.BUILDING_STATUS_AVAILABLE

    def restore_tile(
        self, topleft: pygame.Vector2, chunk: Chunk, building_od: BuildingOD
    ):
        tile_pos = (
            int(topleft.x - chunk.world_topleft.x),
            int(topleft.y - chunk.world_topleft.y),
        )
        tile_data = chunk.get_tile(tile_pos)
        hitbox = pygame.FRect(topleft, (1, 1))
        if tile_data is not None:
            tile_data[0] = building_od.restore_tile.uid
            tile_data[1] = 1
        else:
            chunk.tiles_mat[chunk.get_tile_index(tile_pos)] = [
                building_od.restore_tile.uid,
                1,
                0,
                constants.TILE_PLACED,
            ]
        chunk.tile_hitboxes.append(hitbox)
        chunk.tile_hitboxes_table[tile_pos] = hitbox
        self.refresh_chunk(chunk)

    def place_building(self, building_od: BuildingOD, pos, player: Player):
        status = self.can_place_building(building_od, pos, player)
        if status != constants.BUILDING_STATUS_AVAILABLE:
            return
        if not player.inventory.has(building_od.item, 1):
            return
        player.inventory.remove(building_od.item, 1)
        ray = self.raycast(pos, constants.RAYCASTFLAG_CHUNK)
        if ray is None:
            return
        chunk = self.chunks[ray.chunk_key]
        topleft = shared.get_building_topleft(pos, building_od.size)
        if building_od.restore_tile is not None:
            self.restore_tile(topleft, chunk, building_od)
            return
        bid = self.get_building_id()
        building = Building(bid, building_od, topleft, chunk)
        chunk.building_ids.add(building.id)
        if building_od.floor:
            chunk.building_floor_hitboxes.append(building.hitbox)
        for x in range(building_od.size[0]):
            for y in range(building_od.size[1]):
                tile_pos = (
                    int(topleft.x + x - chunk.world_topleft.x),
                    int(topleft.y + y - chunk.world_topleft.y),
                )
                if tile_pos[0] == pygame.math.clamp(
                    tile_pos[0], 0, constants.CHUNK_SIZE - 1
                ) and tile_pos[1] == pygame.math.clamp(
                    tile_pos[1], 0, constants.CHUNK_SIZE - 1
                ):
                    chunk.building_ids_table[tile_pos] = building.id
                else:
                    b_cpos = shared.get_chunk_pos(
                        (
                            tile_pos[0] + 0.5 + chunk.world_topleft.x,
                            tile_pos[1] + 0.5 + chunk.world_topleft.y,
                        )
                    )
                    b_ckey = shared.get_chunk_key(b_cpos)
                    b_chunk = self.chunks[b_ckey]
                    world_tile_pos = (
                        tile_pos[0] + chunk.world_topleft.x,
                        tile_pos[1] + chunk.world_topleft.y,
                    )
                    new_tile_pos = (
                        int(world_tile_pos[0] - b_chunk.world_topleft.x),
                        int(world_tile_pos[1] - b_chunk.world_topleft.y),
                    )
                    if new_tile_pos not in b_chunk.building_ids_table:
                        b_chunk.building_ids_table[new_tile_pos] = building.id
                    if b_chunk not in building.bordering_chunks:
                        building.bordering_chunks.append(b_chunk)
        self.buildings[building.id] = building
        self.refresh_chunk(chunk)
        return building

    def raycast(self, pos, flag=constants.RAYCASTFLAG_INFO):
        pos = pygame.Vector2(pos)
        chunk_pos = shared.get_chunk_pos(pos)
        chunk_key = shared.get_chunk_key(chunk_pos)
        if chunk_key not in self.chunks:
            return None
        if flag == constants.RAYCASTFLAG_CHUNK:
            return shared.RaycastHit(
                chunk_key, None, constants.RAYCAST_EMPTY, None, None, None, None
            )
        chunk = self.chunks[chunk_key]
        tile_pos = (
            int(pos.x - chunk.world_topleft.x),
            int(pos.y - chunk.world_topleft.y),
        )
        building_id = chunk.building_ids_table.get(tile_pos, None)
        if building_id is not None and building_id in self.buildings:
            building = self.buildings[building_id]
            if flag != constants.RAYCASTFLAG_COLLIDER or building.building_od.floor:
                return shared.RaycastHit(
                    chunk_key,
                    building.hitbox,
                    constants.RAYCAST_BUILDING,
                    building.building_od,
                    tile_pos,
                    None,
                    building.get_raycast_data(),
                )
        if tile_pos in chunk.tile_hitboxes_table or flag == constants.RAYCASTFLAG_ALL:
            tile_data = chunk.get_tile(tile_pos)
            return shared.RaycastHit(
                chunk_key,
                chunk.tile_hitboxes_table.get(tile_pos, None),
                constants.RAYCAST_TILE,
                TileOD.get(tile_data[0]) if tile_data is not None else None,
                tile_pos,
                tile_data,
                None,
            )

    def get_building_id(self):
        new_id = "".join(
            [
                random.choice(constants.BUILDING_ID_ALPHABET)
                for _ in range(constants.BUILDING_ID_LEN)
            ]
        )
        while new_id in self.buildings:
            new_id = "".join(
                [
                    random.choice(constants.BUILDING_ID_ALPHABET)
                    for _ in range(constants.BUILDING_ID_LEN)
                ]
            )
        return new_id

    def frame(self):
        self.dt = self.clock.tick_busy_loop(constants.SERVER_FPS) / 1000
        god.dt = self.dt
        god.dt = pygame.math.clamp(god.dt, 0, 1 / 60)
        checked_chunks_for_drops = set()
        for player in self.players.values():
            drops_data = self.refresh_player_chunks(player, checked_chunks_for_drops)
            hitbox = player.hitbox
            colliding = self.get_chunks_collding_rect(hitbox, 0.1, 0.2)
            rects = sum(
                [
                    chunk.tile_hitboxes + chunk.building_floor_hitboxes
                    for chunk in colliding
                ],
                start=[],
            )
            player.raycast = self.raycast(player.client_mouse_pos)
            player.frame(rects, drops_data)
        timerc.frame()
