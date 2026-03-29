import typing

import pygame

from src.server import god
from src.object_data import BuildingOD
from src.server.inventory import BuildingInventory

if typing.TYPE_CHECKING:
    from src.server.chunk import Chunk
    from src.server.player import Player
    from src.server.energy import EnergyConn

EnergyConn_t: type["EnergyConn"] = None


class BuildingExt:
    _registered_extensions_: dict[str, type["BuildingExt"]] = {}

    def __init__(self, building: "Building"):
        self.building = building
        self.disrupt_alert = False
        self.energy_conns: list["EnergyConn"] = []
        self.destroyed = False
        self.inventories: dict[str, BuildingInventory] = {
            "in": None,
            "out": None,
            "upgrade": None,
        }
        self.init()

    def __init_subclass__(cls, name_id: str):
        BuildingExt._registered_extensions_[name_id] = cls

    @classmethod
    def create_ext(self, building: "Building") -> typing.Self:
        return BuildingExt._registered_extensions_.get(
            building.building_od.name_id, BuildingExt
        )(building)

    @property
    def in_inv(self):
        return self.inventories["in"]

    @property
    def out_inv(self):
        return self.inventories["out"]

    def init(self): ...

    def get_inventories_data(self):
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

    def send_energy_activation(self): ...

    def on_energy_awake(self): ...

    def on_energy_sleep(self): ...

    def on_inventory_dirty(self):
        self.building.refresh_interact()


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
        self.ext.on_destroy()

    def get_raycast_data(self):
        return [self.id, self.state, self.has_energy]

    def get_client_data(self):
        return [
            self.id,
            self.building_od.uid,
            int(self.hitbox.x),
            int(self.hitbox.y),
            self.state,
            self.has_energy,
        ]
