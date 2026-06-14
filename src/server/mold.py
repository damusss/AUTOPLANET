import math
import random
from functools import partial

import pygame

from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.object_data import TileOD
from src.server.chunk import Chunk
from src.server.building import StaticBuilding


class MoldSystem:
    def __init__(self):
        self.mold_patch_od: TileOD = TileOD.objects.mold_patch
        self.ammonia_deposit_od: TileOD = TileOD.objects.ammonia_deposit

    def get_affected_chunks_and_hitbox(self, building: StaticBuilding, radius: int):
        hitbox = pygame.FRect(
            0,
            0,
            building.hitbox.width + radius * 2,
            building.hitbox.height + radius * 2,
        ).move_to(center=building.hitbox.center)
        chunks = god.world.get_chunks_colliding_aligned_rect(pygame.Rect(hitbox))
        return chunks, hitbox

    def iter_affected_chunk_tiles(self, chunks: set[Chunk], hitbox: pygame.FRect):
        for chunk in chunks:
            rel_hitbox = pygame.Rect(hitbox.move(-chunk.world_topleft)).clip(
                pygame.Rect(0, 0, constants.CHUNK_SIZE, constants.CHUNK_SIZE)
            )
            for rel_x in range(rel_hitbox.left, rel_hitbox.right):
                for rel_y in range(rel_hitbox.top, rel_hitbox.bottom):
                    yield (
                        chunk.tiles_mat[chunk.get_tile_index((rel_x, rel_y))],
                        chunk,
                        (rel_x, rel_y),
                    )
            chunk.refresh()

    def get_potential_energy_strength(self, building: StaticBuilding, pos: pygame.Vector2):
        if building.hitbox.collidepoint(pos):
            return constants.POTENTIAL_ENERGY_BUILDING_SPREAD_RADIUS
        dist_x = (
            abs(building.hitbox.centerx - pos.x)
            - building.building_od.size[0] / 2
            + 0.5
        )
        dist_y = (
            abs(building.hitbox.centery - pos.y)
            - building.building_od.size[1] / 2
            + 0.5
        )
        dist = math.sqrt(dist_x**2 + dist_y**2)
        if dist > constants.POTENTIAL_ENERGY_BUILDING_SPREAD_RADIUS:
            return 0
        strength = constants.POTENTIAL_ENERGY_BUILDING_SPREAD_RADIUS - dist
        return max(int(strength), 1)

    def on_placed_or_purged_or_sanitized(
        self, building: StaticBuilding, purged=False, sanitizer=False
    ):
        if not building.building_od.need_energy and not sanitizer:
            return
        chunks, hitbox = self.get_affected_chunks_and_hitbox(
            building,
            constants.SANITIZER_SQUARE_RADIUS
            if sanitizer
            else constants.POTENTIAL_ENERGY_BUILDING_SPREAD_RADIUS,
        )
        for tile_data, chunk, tile_pos in self.iter_affected_chunk_tiles(
            chunks, hitbox
        ):
            if tile_data is None:
                continue
            tile_center = chunk.world_topleft + tile_pos + (0.5, 0.5)
            strength = self.get_potential_energy_strength(building, tile_center)
            add_to_existing = False
            if strength <= 0:
                continue
            if len(tile_data) == 3 and not purged:
                if sanitizer:
                    tile_data.append([0, 0, 0, 1])
                else:
                    tile_data.append([strength, 1, 0, 0])
                    if tile_data[0] == self.mold_patch_od.uid:
                        self.deploy_first_infection(tile_center, strength)
            elif len(tile_data) == 4:
                if isinstance(tile_data[constants.MOLD_I], str):
                    if not purged:
                        if sanitizer:
                            tile_data.insert(constants.MOLD_I, [0, 0, 0, 1])
                        else:
                            tile_data.insert(constants.MOLD_I, [strength, 1, 0, 0])
                            if tile_data[0] == self.mold_patch_od.uid:
                                self.deploy_first_infection(tile_center, strength)
                else:
                    add_to_existing = True

            elif len(tile_data) == 5:
                add_to_existing = True
            if add_to_existing:
                if sanitizer:
                    tile_data[constants.MOLD_I][constants.SANITIZERS_I] += 1
                else:
                    if not purged:
                        tile_data[constants.MOLD_I][constants.POTENTIAL_I] += strength
                        tile_data[constants.MOLD_I][constants.POTENTIAL_COUNT_I] += 1
                    if self.is_infection_source_here(tile_center, tile_only=True)[0]:
                        self.deploy_first_infection(
                            tile_center,
                            tile_data[constants.MOLD_I][constants.POTENTIAL_I],
                            tile_data[constants.MOLD_I][constants.POTENTIAL_COUNT_I],
                        )
        if purged:
            return
        for chunk in chunks:
            for build in chunk.buildings:
                if build.hitbox.colliderect(hitbox):
                    if sanitizer:
                        build.mold_sanitizers += 1
                    else:
                        strength = self.get_potential_energy_strength(
                            building, pygame.Vector2(build.hitbox.center)
                        )
                        build.mold_potential += strength
                        build.mold_potential_count += 1
                        if build.moldy and build.building_od.floor:
                            self.deploy_first_infection(
                                pygame.Vector2(build.hitbox.center),
                                build.mold_potential,
                                build.mold_potential_count,
                            )

    def on_destroyed_or_unsanitized(self, building: StaticBuilding, sanitizer=False):
        if not building.building_od.need_energy and not sanitizer:
            return
        chunks, hitbox = self.get_affected_chunks_and_hitbox(
            building,
            constants.SANITIZER_SQUARE_RADIUS
            if sanitizer
            else constants.POTENTIAL_ENERGY_BUILDING_SPREAD_RADIUS,
        )
        for tile_data, chunk, tile_pos in self.iter_affected_chunk_tiles(
            chunks, hitbox
        ):
            if tile_data is None:
                continue
            tile_center = chunk.world_topleft + tile_pos + (0.5, 0.5)
            strength = self.get_potential_energy_strength(building, tile_center)
            if strength <= 0:
                continue
            if len(tile_data) == 3:
                continue
            if len(tile_data) == 4:
                if isinstance(tile_data[constants.MOLD_I], str):
                    continue
            if sanitizer:
                tile_data[constants.MOLD_I][constants.SANITIZERS_I] -= 1
            else:
                tile_data[constants.MOLD_I][constants.POTENTIAL_I] -= strength
                tile_data[constants.MOLD_I][constants.POTENTIAL_COUNT_I] -= 1
            if tile_data[constants.MOLD_I] == [0, 0, 0, 0]:
                tile_data.pop(3)
        for chunk in chunks:
            for build in chunk.buildings:
                if build.hitbox.colliderect(hitbox):
                    if sanitizer:
                        build.mold_sanitizers -= 1
                    else:
                        strength = self.get_potential_energy_strength(
                            building, pygame.Vector2(build.hitbox.center)
                        )
                        build.mold_potential -= strength
                        build.mold_potential_count -= 1

    def is_infection_source_here(self, pos: pygame.Vector2, tile_only=False):
        ray = god.world.raycast(pos, constants.RAYCASTFLAG_ALL)
        if ray is None:
            return False, 0, 0
        if ray.type != constants.RAYCAST_TILE or ray.tile_data is None:
            if ray.type == constants.RAYCAST_BUILDING and not tile_only:
                if ray.object_data.floor and ray.data[0] in god.world.buildings:
                    building = god.world.buildings[ray.data[0]]
                    if building.moldy:
                        return (
                            True,
                            building.mold_potential,
                            building.mold_potential_count,
                        )
            return False, 0, 0
        tile_data = ray.tile_data
        if tile_data[0] == self.mold_patch_od.uid:
            try:
                return (
                    True,
                    tile_data[constants.MOLD_I][constants.POTENTIAL_I],
                    tile_data[constants.MOLD_I][constants.POTENTIAL_COUNT_I],
                )
            except IndexError:
                return False, 0, 0
        if (
            len(tile_data) > 3
            and isinstance(tile_data[constants.MOLD_I], list)
            and tile_data[constants.MOLD_I][constants.MOLDY_I] == constants.MOLDY
        ):
            if tile_data[constants.MOLD_I][constants.SANITIZERS_I] > 0:
                return False, 0, 0
            return (
                True,
                tile_data[constants.MOLD_I][constants.POTENTIAL_I],
                tile_data[constants.MOLD_I][constants.POTENTIAL_COUNT_I],
            )
        return False, 0, 0

    def can_infect_here(
        self, pos: pygame.Vector2
    ) -> tuple[bool, list | StaticBuilding | None]:
        ray = god.world.raycast(pos, constants.RAYCASTFLAG_ALL)
        if ray is None:
            return False, None
        if ray.type == constants.RAYCAST_TILE:
            tile_data = ray.tile_data
            if not TileOD.get(tile_data[0]).mold_can_infect:
                return False, None
            if len(tile_data) > 3 and isinstance(tile_data[constants.MOLD_I], list):
                if tile_data[constants.MOLD_I][constants.MOLDY_I] == constants.MOLDY:
                    return False, None
                if tile_data[constants.MOLD_I][constants.SANITIZERS_I] > 0:
                    return False, None
            if (
                len(tile_data) < 4
                or isinstance(tile_data[constants.MOLD_I], str)
                or tile_data[constants.MOLD_I][constants.POTENTIAL_I] <= 0
            ):
                return False, None
            return True, tile_data
        elif ray.type == constants.RAYCAST_BUILDING:
            if ray.data is None or ray.data[0] not in god.world.buildings:
                return False, None
            building: StaticBuilding = god.world.buildings[ray.data[0]]
            if building.moldy or building.mold_sanitizers > 0:
                return False, None
            return True, building
        return False, None

    def purge_infection(self, raycast: shared.RaycastHit):
        if raycast.type == constants.RAYCAST_BUILDING:
            if raycast.data[0] in god.world.buildings:
                building: StaticBuilding = god.world.buildings[raycast.data[0]]
                if building.moldy:
                    building.purge_mold()
                    self.on_placed_or_purged_or_sanitized(building, purged=True)
                    return True
        elif raycast.type == constants.RAYCAST_TILE:
            if (
                len(raycast.tile_data) > 3
                and isinstance(raycast.tile_data[constants.MOLD_I], list)
                and raycast.tile_data[constants.MOLD_I][constants.MOLDY_I]
                == constants.MOLDY
            ):
                raycast.tile_data[constants.MOLD_I][constants.MOLDY_I] = (
                    constants.MOLD_FREE
                )
                god.world.chunks[raycast.chunk_key].refresh()
                return True
        return False

    def deploy_first_infection(
        self, source_center: pygame.Vector2, strength: int, count=1
    ):
        available_count = 0
        for offset in constants.MOLD_SPREAD_DIRECTIONS:
            if self.can_infect_here(source_center + offset):
                available_count += 1
                break
        if available_count <= 0:
            return
        timerc.add(
            self.get_infection_time(strength, count),
            partial(self.on_mold_infection_complete, source_center),
        )

    def get_infection_time(self, strength: int, count: int):
        rel_strength = strength / count
        close_percentage = (
            rel_strength / constants.POTENTIAL_ENERGY_BUILDING_SPREAD_RADIUS
        )
        time = (
            constants.MOLD_INFECTION_BASE_TIME
            - constants.MOLD_INFECTION_BASE_TIME * close_percentage
        )
        time -= time / 10 * count
        time = max(time, 0)
        return (
            time + constants.MOLD_INFECTION_MINUMUM_TIME + random.uniform(0, time / 10)
        )

    def on_mold_infection_complete(self, source_center: pygame.Vector2):
        is_infection_source, source_strength, source_strength_count = (
            self.is_infection_source_here(source_center)
        )
        if not is_infection_source:
            return
        valid_loc_datas: list[tuple[int, list | StaticBuilding, pygame.Vector2]] = []
        for offset in constants.MOLD_SPREAD_DIRECTIONS:
            pos = source_center + offset
            can_infect, loc_data = self.can_infect_here(pos)
            if not can_infect:
                continue
            if isinstance(loc_data, StaticBuilding):
                sort_energy = loc_data.mold_potential
            else:
                sort_energy = loc_data[constants.MOLD_I][constants.POTENTIAL_I]
            if sort_energy <= source_strength:
                continue
            valid_loc_datas.append((sort_energy, loc_data, pos))
        if len(valid_loc_datas) <= 0:
            return
        chosen_loc = sorted(valid_loc_datas, key=lambda i: i[0], reverse=True)[0]
        sort_energy, loc_data, loc_pos = chosen_loc
        continue_infection = False
        strength = strength_count = 1
        if isinstance(loc_data, StaticBuilding):
            loc_data.make_moldy()
            if loc_data.building_od.floor:
                continue_infection = True
                strength = loc_data.mold_potential
                strength_count = loc_data.mold_potential_count
        else:
            loc_data[constants.MOLD_I][constants.MOLDY_I] = constants.MOLDY
            strength = loc_data[constants.MOLD_I][constants.POTENTIAL_I]
            strength_count = loc_data[constants.MOLD_I][constants.POTENTIAL_COUNT_I]
            continue_infection = True
            chunk_key = shared.get_chunk_key(shared.get_chunk_pos(loc_pos))
            if chunk_key in god.world.chunks:
                god.world.chunks[chunk_key].refresh()
        if continue_infection:
            timerc.add(
                self.get_infection_time(strength, strength_count),
                partial(self.on_mold_infection_complete, loc_pos),
            )
        if len(valid_loc_datas) > 1:
            timerc.add(
                self.get_infection_time(source_strength, source_strength_count),
                partial(self.on_mold_infection_complete, source_center),
            )
