import math
import typing
from functools import partial

import pygame

from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.object_data import BuildingOD
from src.server.inventory import BuildingInventory

if typing.TYPE_CHECKING:
    from src.server.chunk import Chunk
    from src.server.player import Player
    from src.server.energy import EnergyConn

EnergyConn_t: type["EnergyConn"] = None


class CommonBuildingExt:
    def __init__(self, building: "Building|MovingBuilding"):
        self.building = building
        self.destroyed = False
        self.inventories: dict[str, BuildingInventory | None] = {
            "in": None,
            "out": None,
            "upgrade": None,
        }

    @property
    def in_inv(self):
        return self.inventories["in"]

    @property
    def out_inv(self):
        return self.inventories["out"]

    def init(self): ...
    def on_place(self): ...
    def on_client_config(self, mail: shared.Mail): ...

    def on_destroy(self):
        self.drop_inventories()

    def drop_inventories(self):
        for inv in self.inventories.values():
            if inv is None:
                continue
            else:
                for slot in inv.slots:
                    if slot.empty:
                        continue
                    god.world.drop(
                        shared.get_drop_random_pos(self.building.hitbox),
                        slot.item,
                        slot.amount,
                    )

    def get_inventories_data(self) -> dict:
        data = {"inventories": {}}
        added = set()
        for name, inv in self.inventories.items():
            if inv in added:
                data["inventories"][name] = None
            else:
                data["inventories"][name] = (
                    inv.get_client_data() if inv is not None else None
                )
                added.add(inv)
        return data

    def get_client_data(self):
        return self.get_inventories_data()

    def on_inventory_dirty(self):
        self.building.refresh_interact()

    def get_extra_raycast_data(self): ...

    def get_config(self):
        return {}


class MovingBuildingExt(CommonBuildingExt):
    building: "MovingBuilding"
    REGISTERED_EXTENSIONS: dict[str, type["MovingBuildingExt"]] = {}

    def __init__(self, building: "MovingBuilding"):
        super().__init__(building)
        self.init()

    def __init_subclass__(cls, name_id: str):
        MovingBuildingExt.REGISTERED_EXTENSIONS[name_id] = cls

    @classmethod
    def create_ext(cls, building: "MovingBuilding") -> "MovingBuildingExt":
        return MovingBuildingExt.REGISTERED_EXTENSIONS.get(
            building.building_od.name_id, MovingBuildingExt
        )(building)

    def on_reach(self, target: "Building|None", kind: str | None): ...

    def get_inventories_data(self):
        data = super().get_inventories_data()
        data["building_id"] = self.building.id
        return data

    def get_display_data(self): ...


class BuildingExt(CommonBuildingExt):
    building: "Building"
    REGISTERED_EXTENSIONS: dict[str, type["BuildingExt"]] = {}

    def __init__(self, building: "Building"):
        super().__init__(building)
        self.disrupt_alert = False
        self.energy_conns: list["EnergyConn"] = []
        self.init()

    def __init_subclass__(cls, name_id: str):
        BuildingExt.REGISTERED_EXTENSIONS[name_id] = cls

    @classmethod
    def create_ext(cls, building: "Building") -> "BuildingExt":
        return BuildingExt.REGISTERED_EXTENSIONS.get(
            building.building_od.name_id, BuildingExt
        )(building)

    def can_provide_energy(self):
        return False

    def on_place(self):
        if not self.building.building_od.need_energy:
            return
        for provider in self.building.chunk.get_energy_providers_for_rect(
            self.building.hitbox
        ):
            conn = EnergyConn_t(self, provider.building.ext).finalize()
            if provider.building.has_energy:
                self.on_conn_activated(conn)

    def on_destroy(self):
        self.destroyed = True
        for conn in list(self.energy_conns):
            conn.destroy()

    def on_conn_activated(self, conn: "EnergyConn"):
        if self.disrupt_alert:
            self.disrupt_alert = False
            if self.building.id in god.world.disrupt_alerted_buildings:
                god.world.disrupt_alerted_buildings.remove(self.building.id)
            return
        if self.building.has_energy:
            return
        self.building.has_energy = True
        self.on_energy_awake()
        self.building.refresh_interact()
        self.building.chunk.refresh()

    def on_conn_disrupted(self, conn: "EnergyConn", state: set):
        if self.building.id in state:
            return
        state.add(self.building.id)
        if not self.building.has_energy:
            return
        self.disrupt_alert = True
        if self.building.id not in god.world.disrupt_alerted_buildings:
            god.world.disrupt_alerted_buildings.add(self.building.id)
        for tconn in self.energy_conns:
            if conn == tconn:
                continue
            tconn.disrupted(self, state)

    def finalize_energy_disrupt(self):
        self.disrupt_alert = False
        self.building.has_energy = False
        self.on_energy_sleep()
        self.building.refresh_interact()
        self.building.chunk.refresh()

    def send_energy_activation(self): ...

    def on_energy_awake(self): ...

    def on_energy_sleep(self): ...

    def get_extra_data(self): ...


class Building:
    def __init__(self, id_: str, building_od: BuildingOD, topleft, chunk):
        self.id = id_
        self.building_od = building_od
        self.hitbox = pygame.FRect(topleft, building_od.size)
        self.chunk: "Chunk" = chunk
        self.bordering_chunks: list["Chunk"] = []
        self.state = self.building_od.states["default"].name
        self.has_energy = False
        self.require_floor = True
        self.bots_endpoint = {}
        self.subscribed_client_players: list["Player"] = []
        self.ext = BuildingExt.create_ext(self)

    def change_state(self, state):
        if self.state == state:
            return
        self.state = state
        self.refresh_interact()
        self.chunk.refresh()

    def refresh_interact(self):
        if len(self.subscribed_client_players) <= 0:
            return
        god.world.refresh_building_interact(self)

    def on_place(self):
        self.ext.on_place()

    def on_destroy(self):
        for bot_id, endpoint_kind in self.bots_endpoint.items():
            if bot_id in god.world.buildings:
                bot: "MovingBuilding" = god.world.buildings[bot_id]
                bot.trajectory[endpoint_kind] = None
                other = bot.trajectory[shared.other_kind(endpoint_kind)]
                bot.refresh_trajectory()
                if other is not None:
                    other.chunk.refresh()
        self.bots_endpoint = set()
        self.ext.on_destroy()
        self.refresh_interact()

    def get_raycast_data(self, raycast_flag):
        if raycast_flag == constants.RAYCASTFLAG_INFO:
            extra_data = self.ext.get_extra_raycast_data()
            if extra_data is not None:
                return [self.id, self.state, self.has_energy, extra_data]
        return [self.id, self.state, self.has_energy]

    def get_client_data(self):
        data: list = [
            self.id,
            self.building_od.uid,
            int(self.hitbox.x),
            int(self.hitbox.y),
            self.state,
            self.has_energy,
        ]
        extra = self.ext.get_extra_data()
        if extra is not None:
            data.append(extra)
        return data


class MovingBuilding:
    def __init__(self, id_: str, building_od: BuildingOD, center, chunk_key):
        self.id = id_
        self.reach_id = None
        self.building_od = building_od
        self.center = pygame.Vector2(center)
        self.subscribed_client_players: list["Player"] = []
        self.moving = False
        self.move_target: Building | None = None
        self.target_kind: str | None = None
        self.last_known_center = self.center
        self.last_known_time = 0
        self.last_known_direction = pygame.Vector2(-1, 0)
        self.speed_ps = constants.BOT_SPEED_PS
        self.trajectory_chunks = set()
        self.temporary_trajectory_chunks = set()
        self.trajectory: dict[str, Building | None] = {
            "in": None,
            "out": None,
        }
        self.update_trajectory_chunks([chunk_key])
        self.ext = MovingBuildingExt.create_ext(self)

    @property
    def hitbox(self):
        return pygame.FRect(
            0,
            0,
            self.building_od.size[0] * self.building_od.hitbox_multiplier,
            self.building_od.size[1] * self.building_od.hitbox_multiplier,
        ).move_to(center=self.center)

    def collapse_position(self):
        if self.moving and not god.world.paused:
            self.center = self.last_known_center + self.last_known_direction * (
                ((god.world.get_ticks() - self.last_known_time) / 1000) * self.speed_ps
            )

    def refresh_trajectory(self):
        self.moving = False
        self.reach_id = None
        here = shared.get_chunk_pos(self.center)
        herek = shared.get_chunk_key(here)
        chunks = {herek}
        a = b = None
        if self.trajectory["in"] is not None:
            a = pygame.Vector2(self.trajectory["in"].hitbox.center)
        if self.trajectory["out"] is not None:
            b = pygame.Vector2(self.trajectory["out"].hitbox.center)
        if (
            a is None
            or b is None
            or a.distance_to(b) > constants.BOT_TRAJECTORY_MAX_SIZE
        ):
            self.update_trajectory_chunks(chunks)
            return
        main_chunks = shared.get_trajectory_chunks(a, b)
        reach_a_chunks = shared.get_trajectory_chunks(self.center, a)
        self.temporary_trajectory_chunks = reach_a_chunks.difference(main_chunks)
        chunks = chunks.union(main_chunks, reach_a_chunks)
        self.update_trajectory_chunks(chunks)
        self.depart(self.trajectory["in"], constants.INVENTORY_KIND_INPUT)

    def depart(self, target: Building | None, kind):
        if target is None:
            return
        self.moving = True
        self.last_known_center = self.center
        self.last_known_time = god.world.get_ticks()
        self.move_target = target
        self.target_kind = kind
        self.last_known_direction = (target.hitbox.center - self.center).normalize()
        distance = self.center.distance_to(target.hitbox.center)
        time = distance / self.speed_ps
        reach_id = shared.get_building_id()
        self.reach_id = reach_id
        timerc.add(time, partial(self.on_reach, reach_id))

    def on_reach(self, reach_id):
        if reach_id != self.reach_id:
            return
        self.center = pygame.Vector2(self.move_target.hitbox.center)
        if len(self.temporary_trajectory_chunks) > 0:
            self.partial_remove_trajectory(self.temporary_trajectory_chunks)
            self.temporary_trajectory_chunks = set()
        if self.trajectory["in"] is None or self.trajectory["out"] is None:
            self.refresh_trajectory()
            return
        self.ext.on_reach(self.move_target, self.target_kind)
        new_kind = shared.other_kind(self.target_kind)
        self.depart(self.trajectory[new_kind.removesuffix("put")], new_kind)

    def partial_remove_trajectory(self, chunk_keys):
        for ckey in chunk_keys:
            if ckey in god.world.chunks:
                chunk = god.world.chunks[ckey]
                if self.id in chunk.moving_building_ids:
                    chunk.moving_building_ids.remove(self.id)

    def update_trajectory_chunks(self, chunk_keys):
        self.partial_remove_trajectory(self.trajectory_chunks)
        self.trajectory_chunks = set()
        for ckey in chunk_keys:
            if ckey in god.world.chunks:
                chunk = god.world.chunks[ckey]
                chunk.moving_building_ids.add(self.id)
                self.trajectory_chunks.add(ckey)

    def refresh_interact(self):
        if len(self.subscribed_client_players) <= 0:
            return
        god.world.refresh_building_interact(self)

    def on_place(self):
        self.ext.on_place()

    def on_destroy(self):
        self.ext.on_destroy()
        self.refresh_interact()

    def get_raycast_data(self, raycast_flag):
        if raycast_flag == constants.RAYCASTFLAG_INFO:
            extra_data = self.ext.get_extra_raycast_data()
            if extra_data is not None:
                return [self.id, "", extra_data]
        return [self.id, ""]

    def get_client_data(self):
        return [
            self.building_od.uid,
            round(self.center.x, constants.DIGIT_PRECISION),
            round(self.center.y, constants.DIGIT_PRECISION),
            math.copysign(1, self.last_known_direction.x),
            {
                name: (
                    None
                    if val is None
                    else (
                        [val.id, tuple(val.hitbox), val.building_od.debug_attach_offset]
                    )
                )
                for name, val in self.trajectory.items()
            },
            self.ext.get_display_data(),
        ]
