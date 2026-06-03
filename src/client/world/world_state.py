import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ResearchNodeOD, ItemOD
from src.client.world.chunk import Chunk, BuildingDataHolder
from src.client.world.camera import Camera
from src.client.world.world_rendering import WorldRendering
from src.client.world.player import Player, OtherPlayer


class WorldState:
    def __init__(self, rendering):
        god.world = self
        self.dt = 0
        self.fps = 0
        self.paused = False
        self.cumulative_pause_ticks = 0
        self.clock = pygame.Clock()
        self.rendering: WorldRendering = rendering
        self.player = Player()
        self.camera = Camera()
        self.loaded_chunks: dict[str, Chunk] = {}
        self.visible_lights = [self.player.light]
        self.no_energy_buildings: list[BuildingDataHolder] = []
        self.other_players: dict[int, OtherPlayer] = {}
        self.drops_data = []
        self.moving_buildings_data = {}
        self.bots_anim_offset = {}
        self.unlocked_items: set[ItemOD] = set()
        self.researched_nodes: set[ResearchNodeOD] = set()
        self.research_progress: dict[ResearchNodeOD, int] = {}
        shared.time_get_ticks = self.get_ticks

    def get_ticks(self):
        return pygame.time.get_ticks() - self.cumulative_pause_ticks

    def other_player_connect(self, player_id, pos, name):
        new_player = self.other_players[player_id] = OtherPlayer(pos, player_id, name)
        self.visible_lights.append(new_player.light)

    def other_player_disconnect(self, player_id):
        if player_id not in self.other_players:
            return
        player = self.other_players[player_id]
        self.visible_lights.remove(player.light)
        self.other_players.pop(player_id)

    def window_resized(self):
        self.rendering.refresh_light_textures()

    def enter(self):
        god.rendering = self.rendering

    def load_chunks(self, chunks, refresh):
        if refresh:
            self.unload_chunks(chunks)
        for ckey, cdata in chunks.items():
            chunk = Chunk(cdata)
            self.loaded_chunks[ckey] = chunk
            for light in chunk.lights:
                self.visible_lights.insert(0, light)
            for bd in chunk.static_buildings:
                if not bd.has_energy and bd.building_od.need_energy:
                    self.no_energy_buildings.append(bd)

    def unload_chunks(self, chunks):
        for ckey in chunks:
            if ckey in self.loaded_chunks:
                chunk = self.loaded_chunks.pop(ckey)
                chunk.unload()
                for light in chunk.lights:
                    try:
                        self.visible_lights.remove(light)
                    except ValueError:
                        ...
                for bd in chunk.static_buildings:
                    if not bd.has_energy and bd.building_od.need_energy:
                        try:
                            self.no_energy_buildings.remove(bd)
                        except ValueError:
                            ...

    def frame(self):
        ms = self.clock.tick(constants.CLIENT_FPS)
        god.dt = self.dt = (not self.paused) * (ms / 1000)
        self.cumulative_pause_ticks += self.paused * ms

        self.camera.frame()
        self.player.frame()
        for other_player in self.other_players.values():
            other_player.frame()

        self.fps = self.clock.get_fps()
        god.windowing.window.title = f"Client {self.fps:.0f} FPS"

        self.rendering.render()

    def event(self, e): ...
