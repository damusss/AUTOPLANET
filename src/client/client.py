import os
import subprocess
from queue import Queue

import pygame

from src import shared
from src import mailbox
from src import constants
from src import object_data
from src.client import god
from src.client.input import Input
from src.client.assets import Assets
from src.client.windowing import Windowing
from src.client.connection import SocketConnection
from src.client.main_menu_state import MainMenuState
from src.client.world.world_state import WorldState
from src.client.world.world_rendering import WorldRendering


class Client:
    def __init__(self):
        god.client = self
        object_data.load_all("assets/objects")
        self.abort = False
        self.windowing = Windowing()
        world_renderering = WorldRendering()
        self.assets = Assets()
        self.world = WorldState(world_renderering)
        self.main_menu = MainMenuState()
        self.input = Input()
        self.enter_state(self.main_menu)
        self.mailbox = Queue()
        self.id = -1
        self.name = f"local_{os.getpid()}"
        self.conn = SocketConnection(self)
        self.offline_localhost_server_process = None
        self.last_mail = None

    def enter_state(self, state: WorldState | MainMenuState):
        self.state = state
        self.state.enter()

    def handle_mail(self, mail: mailbox.Mail):
        self.last_mail = pygame.time.get_ticks()
        if mail.type == mailbox.MAIL_CONNECTION_ACCEPTED:
            self.conn.connection_accepted(mail)
            self.enter_state(self.world)
            print(
                f"[C:{self.id}] Connected to server 'local' (client name={self.name})"
            )
            for player in mail.other_players:
                self.world.other_player_connect(player[0], player[1], player[2])
        elif mail.type == mailbox.MAIL_FORCE_DISCONNECT:
            self.conn.force_disconnected()
            self.enter_state(self.main_menu)
            print(
                f"[C:/{self.id}] Kicked from server 'local' (client name={self.name})"
            )
        elif mail.type == mailbox.MAIL_PLAYER_PHYSICS:
            self.world.player.pos = pygame.Vector2(mail.pos)
            self.world.player.vel = pygame.Vector2(mail.vel)
            self.world.player.energy = mail.energy
            self.world.player.raycast = (
                shared.RaycastHit.from_client_data(mail.raycast)
                if mail.raycast
                else None
            )
            self.world.drops_data = mail.drops
            self.world.player.craft_queue = [
                shared.CraftQueueItem.from_client_data(data)
                for data in mail.craft_queue
            ]

            for other_player_id, other_player_data in mail.other_players.items():
                other_player_id = int(other_player_id)
                if other_player_id not in self.world.other_players:
                    continue
                other_player = self.world.other_players[other_player_id]
                other_player.pos = pygame.Vector2(other_player_data["pos"])
                other_player.vel = pygame.Vector2(other_player_data["vel"])
                other_player.frame_kind = other_player_data["frame_kind"]
                other_player.frame_index = other_player_data["frame_index"]

        elif mail.type == mailbox.MAIL_PLAYER_STATS:
            self.world.player.health = mail.health
            self.world.player.update_inventory(mail.inventory)
        elif mail.type == mailbox.MAIL_CHUNK_LOAD:
            self.world.load_chunks(mail.chunks, mail.refresh)
        elif mail.type == mailbox.MAIL_CHUNK_UNLOAD:
            self.world.unload_chunks(mail.chunk_keys)
        elif mail.type == mailbox.MAIL_OTHER_PLAYER_CONNECT:
            self.world.other_player_connect(mail.player_id, mail.pos, mail.name)
        elif mail.type == mailbox.MAIL_OTHER_PLAYER_DISCONNECT:
            self.world.other_player_disconnect(mail.player_id)
        elif mail.type == mailbox.MAIL_BREAK_START:
            time = mail.time
            if time == "now":
                time = pygame.time.get_ticks()
            self.world.player.break_start_time = time
        elif mail.type == mailbox.MAIL_BUILDING_AVAILABLE:
            self.world.player.building_available = mail.available

    def disconnect(self):
        self.mailbox.queue.clear()
        self.last_mail = None
        self.conn.mail_disconnect()
        self.enter_state(self.main_menu)

    def quit(self):
        self.abort = True
        self.disconnect()
        if constants.OFFLINE_LOCALHOST:
            self.conn.mail(mailbox.MAIL_ABORT)
        print(
            f"[C:/{self.id}] Disconnected from server 'local' (client name={self.name})"
        )

    def frame(self):
        if (
            self.last_mail is not None
            and pygame.time.get_ticks() - self.last_mail
            >= constants.CLIENT_TIMEOUT * 1000
        ):
            print(f"[C:{self.id}] Server timeout, disconnecting")
            self.disconnect()
            return

        self.windowing.frame()
        for event in pygame.event.get():
            signal = self.windowing.event(event)
            if signal == "abort":
                self.quit()
                return
            if event.type == pygame.USEREVENT:
                print("user", event)

            self.input.event(event)
            self.state.event(event)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:  # temp
                if constants.OFFLINE_LOCALHOST:
                    if self.offline_localhost_server_process is None:
                        self.offline_localhost_server_process = subprocess.Popen(
                            f"python main_server.py -client_PID {os.getpid()}"
                        )

                self.conn.mail_connect()
                print(f"[C:{self.name}] Sent connection request to server 'local'")

            elif event.type == pygame.WINDOWRESIZED:
                self.state.window_resized()

        while self.mailbox.qsize() > 0:
            self.handle_mail(self.mailbox.get())

        self.input.frame()
        self.state.frame()
        self.conn.frame()
