import pygame

from src import shared
from src import constants
from src.server import god
from src.object_data import VegetationOD
from src.server.building import Building, BuildingExt


class EnergyProvider:
    def __init__(self, building: "Building"):
        self.building = building
        self.id = self.building.id
        self.center = pygame.Vector2(building.hitbox.center)
        self.radius = building.building_od.energy_radius

    def __hash__(self):
        return hash(self.id)


class EnergyConn:
    def __init__(self, a: BuildingExt, b: BuildingExt):
        self.a = a
        self.b = b
        self.endpoints = [self.a, self.b]
        self.alive = True

    def activate(self, source: BuildingExt):
        self.other_endpoint(source).on_conn_activated(self)

    def disrupted(self, source: BuildingExt, state):
        self.other_endpoint(source).on_conn_disrupted(self, state)

    def other_endpoint(self, endpoint: BuildingExt) -> BuildingExt:
        for e in self.endpoints:
            if e != endpoint:
                return e

    def finalize(self):
        for e in self.endpoints:
            e.energy_conns.append(self)
        return self

    def destroy(self):
        for e in self.endpoints:
            e.energy_conns.remove(self)
        return self

    def get_client_data(self):
        has_energy = False
        for e in self.endpoints:
            if (
                e.building.building_od.energy_endpoint_type
                != constants.ENDPOINT_MACHINE
                and e.building.has_energy
            ):
                has_energy = True
                break
        return [
            tuple(
                self.a.building.hitbox.center
                + pygame.Vector2(self.a.building.building_od.debug_attach_offset)
            ),
            tuple(
                self.b.building.hitbox.center
                + pygame.Vector2(self.b.building.building_od.debug_attach_offset)
            ),
            has_energy,
        ]


class EnergyPlant(BuildingExt, name_id="energy_plant"):
    def init(self):
        self.providing_chunks = set()
        self.provider = EnergyProvider(self.building)
        self.building.has_energy = True
        self.building.change_state("on")

    def can_provide_energy(self):
        return self.building.has_energy

    def on_conn_activated(self, conn): ...

    def on_conn_disrupted(self, conn, state):
        if self.building.id not in god.world.disrupt_alerted_plants:
            god.world.disrupt_alerted_plants.add(self.building.id)

    def on_place(self):
        oxygen_raycasts = [
            god.world.raycast(
                pygame.Vector2(self.building.hitbox.center) + offset,
                constants.RAYCASTFLAG_VEGETATION,
            )
            for offset in ((-0.5, -0.5), (-0.5, 0.5), (0.5, -0.5), (0.5, 0.5))
        ]
        self.building.has_energy = False
        for oxygen_raycast in oxygen_raycasts:
            if (
                oxygen_raycast is not None
                and oxygen_raycast.object_data == VegetationOD.objects.oxygen_plant
            ):
                self.building.has_energy = True
                break
        chunks = god.world.load_or_get_chunks(
            shared.get_chunk_keys_colliding_circle(
                self.provider.center, self.provider.radius
            )
        )
        for chunk in chunks:
            self.providing_chunks.add(chunk.chunk_key)
            for provider in chunk.energy_providers:
                if shared.rect_collide_circle(
                    provider.building.hitbox, self.provider.center, self.provider.radius
                ):
                    EnergyConn(self, provider.building.ext).finalize()
            for building in chunk.buildings:
                if (
                    (
                        building.building_od.energy_endpoint_type
                        == constants.ENDPOINT_MACHINE
                    )
                    and shared.rect_collide_circle(
                        building.hitbox, self.provider.center, self.provider.radius
                    )
                    and building.building_od.need_energy
                ):
                    EnergyConn(self, building.ext).finalize()
            chunk.energy_providers.add(self.provider)
        if self.building.has_energy:
            self.send_energy_activation()

    def send_energy_activation(self):
        for conn in self.energy_conns:
            conn.activate(self)

    def on_destroy(self):
        self.destroyed = True
        for ckey in self.providing_chunks:
            chunk = god.world.chunks[ckey]
            if self.provider in chunk.energy_providers:
                chunk.energy_providers.remove(self.provider)
        self.providing_chunks = set()
        copy = self.energy_conns.copy()
        for conn in list(self.energy_conns):
            conn.destroy()
            conn.other_endpoint(self).building.chunk.refresh()
        god.world.energy_disrupt(self, copy)


class EnergyTransmitter(BuildingExt, name_id="energy_transmitter"):
    def init(self):
        self.providing_chunks = set()
        self.provider = EnergyProvider(self.building)

    def can_provide_energy(self):
        return self.building.has_energy

    def on_place(self):
        chunks = god.world.load_or_get_chunks(
            shared.get_chunk_keys_colliding_circle(
                self.provider.center, self.provider.radius
            )
        )
        already_connected = set()
        for provider in self.building.chunk.get_energy_providers_for_rect(
            self.building.hitbox
        ):
            EnergyConn(self, provider.building.ext).finalize()
            already_connected.add(provider.building.id)
        for chunk in chunks:
            self.providing_chunks.add(chunk.chunk_key)
            for provider in chunk.energy_providers:
                if provider.id in already_connected:
                    continue
                if shared.rect_collide_circle(
                    provider.building.hitbox, self.provider.center, self.provider.radius
                ):
                    EnergyConn(self, provider.building.ext).finalize()
            for building in chunk.buildings:
                if (
                    (
                        building.building_od.energy_endpoint_type
                        == constants.ENDPOINT_MACHINE
                    )
                    and shared.rect_collide_circle(
                        building.hitbox, self.provider.center, self.provider.radius
                    )
                    and building.building_od.need_energy
                ):
                    EnergyConn(self, building.ext).finalize()
            chunk.energy_providers.add(self.provider)
        for conn in self.energy_conns:
            if conn.other_endpoint(self).can_provide_energy():
                self.on_conn_activated(conn)

    def on_destroy(self):
        self.destroyed = True
        for ckey in self.providing_chunks:
            chunk = god.world.chunks[ckey]
            if self.provider in chunk.energy_providers:
                chunk.energy_providers.remove(self.provider)
        self.providing_chunks = set()
        copy = self.energy_conns.copy()
        for conn in list(self.energy_conns):
            conn.destroy()
            conn.other_endpoint(self).building.chunk.refresh()
        god.world.energy_disrupt(self, copy)

    def on_conn_activated(self, conn):
        if self.disrupt_alert:
            self.disrupt_alert = False
            if self.building.id in god.world.disrupt_alerted_buildings:
                god.world.disrupt_alerted_buildings.remove(self.building.id)
            for tconn in self.energy_conns:
                if conn == tconn:
                    continue
                tconn.activate(self)
            return
        if self.building.has_energy:
            return
        self.building.has_energy = True
        self.on_energy_awake()
        for tconn in self.energy_conns:
            if conn == tconn:
                continue
            tconn.activate(self)

    def on_conn_disrupted(self, conn, state):
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

    def on_energy_awake(self):
        self.building.change_state("on")

    def on_energy_sleep(self):
        self.building.change_state("off")
