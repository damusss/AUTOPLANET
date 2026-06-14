import psutil
from queue import Queue

import pygame

from src import shared
from src import constants
from src import object_data
from src.server import god
from src.timerc import timerc
from src.object_data import BuildingOD
from src.server.world import World
from src.server.connection import (
    SocketClientConnection,
    SocketServerConnection,
)


class ClientInterface:
    def __init__(self, id_, data, server):
        self.name = None
        self.id = id_
        self.conn = SocketClientConnection(id_, data, server)
        self.last_heartbeat = god.world.get_ticks()

    def heartbeat(self):
        self.last_heartbeat = god.world.get_ticks()


class Server:
    def __init__(self, client_pid):
        god.server = self
        object_data.load_all("assets/objects")
        self.abort = False
        self.free_client_id = 1
        self.mailbox: Queue[shared.Mail] = Queue()
        self.world = World()
        self.clients: dict[int, ClientInterface] = {}
        self.conn = SocketServerConnection(self)
        self.client_PID = client_pid
        self.last_client_check = god.world.get_ticks()
        self.frozen = False
        if self.client_PID is not None:
            shared.log(
                f"[S] Server started with offline localhost mode (client PID={self.client_PID})"
            )
        else:
            shared.log("[S] Server started with multiplayer mode")

    def freeze(self):
        if self.world.paused:
            self.world.unpause()
        self.frozen = True
        timerc.pause()
        shared.log("[S] Server frozen (no clients connected)")

    def unfreeze(self):
        self.frozen = False
        timerc.resume()
        shared.log("[S] Server unfrozen")

    def handle_mail(self, mail: shared.Mail):
        if mail.compare(constants.MAIL_ABORT):
            if self.client_PID is not None:
                self.abort = True
        elif mail.compare(constants.MAIL_CONNECT):
            id_ = self.free_client_id
            self.free_client_id += 1
            client = ClientInterface(id_, mail.data, self)
            self.clients[id_] = client
            other_players = []
            for player in self.world.players.values():
                player.client.conn.mail(
                    constants.MAIL_OTHER_PLAYER_CONNECT,
                    player_id=client.id,
                    pos=(0, 0),
                    name=client.name,
                )
                other_players.append((player.client.id, (0, 0), player.client.name))
            new_player = self.world.player_connect(client)
            client.conn.mail(
                constants.MAIL_CONNECTION_ACCEPTED, other_players=other_players
            )
            god.world.research.notify_research_info([new_player], True)
            if self.frozen:
                self.unfreeze()
            shared.log(f"[S] Client connection accepted (ID={client.id})")
        elif mail.compare(constants.MAIL_DISCONNECT):
            if mail.client_id in self.clients:
                client = self.clients[mail.client_id]
                self.clients.pop(mail.client_id)
                self.world.player_disconnect(client)
                for player in self.world.players.values():
                    player.client.conn.mail(
                        constants.MAIL_OTHER_PLAYER_DISCONNECT, player_id=client.id
                    )
                shared.log(
                    f"[S] Client disconnected (name={client.name}, ID={client.id})"
                )
            if len(self.clients) <= 0:
                self.freeze()
        elif mail.compare(constants.MAIL_HEARTBEAT):
            if mail.client_id in self.clients:
                self.clients[mail.client_id].heartbeat()
        elif mail.compare(constants.MAIL_NAME):
            if mail.client_id in self.clients:
                self.clients[mail.client_id].name = mail.name
        elif mail.compare(constants.MAIL_INPUT_DIR):
            if mail.client_id in self.clients:
                self.world.players[mail.client_id].client_input_dir = pygame.Vector2(
                    mail.dir
                )
        elif mail.compare(constants.MAIL_INPUT_EVENT):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                if (
                    mail.input_type == pygame.MOUSEBUTTONDOWN
                    and mail.button == pygame.BUTTON_LEFT
                ):
                    player.client_mouse_pressing = True
                if (
                    mail.input_type == pygame.MOUSEBUTTONUP
                    and mail.button == pygame.BUTTON_LEFT
                ):
                    player.client_mouse_pressing = False
                # handle key event when needed. no key reported, but action to allow for key binds
        elif mail.compare(constants.MAIL_MOUSE_POS):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                player.client_mouse_pos = pygame.Vector2(mail.pos)
        elif mail.compare(constants.MAIL_ANIMATION_UPDATE):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                player.client_frame_kind = mail.frame_kind
                player.client_frame_index = mail.frame_index
        elif mail.compare(constants.MAIL_INVENTORY_ACTION):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                player.inventory.client_action(
                    mail.action, mail.source, mail.dest, mail.amount
                )
        elif mail.compare(constants.MAIL_HOTBAR_ACTION):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                player.client_hotbar_action(mail.i, mail.item_uid)
        elif mail.compare(constants.MAIL_CRAFT_REQUEST):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                player.try_craft_item(mail.item_uid)
        elif mail.compare(constants.MAIL_BUILDING_AVAILABLE):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                available = self.world.can_place_building(
                    BuildingOD.get(mail.building_uid), pygame.Vector2(mail.pos), player
                )
                player.client_building_preview = [
                    mail.pos,
                    mail.building_uid,
                    available,
                ]
                player.client_building_preview_clear_after = 10
                player.client.conn.mail(
                    constants.MAIL_BUILDING_AVAILABLE_RESPONSE, available=available
                )
        elif mail.compare(constants.MAIL_PLACE_BUILDING):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                self.world.try_place_building(
                    BuildingOD.get(mail.building_uid), pygame.Vector2(mail.pos), player
                )
        elif mail.compare(constants.MAIL_BUILDING_INTERACT):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                self.world.building_interact(player, mail.building_id, mail.unsubscribe)
        elif mail.compare(constants.MAIL_BOT_TRAJECTORY):
            if mail.bot_id in self.world.buildings and (
                mail.target_id in self.world.buildings or mail.target_id is None
            ):
                self.world.edit_bot_trajectory(
                    self.world.buildings[mail.bot_id],
                    self.world.buildings[mail.target_id]
                    if mail.target_id is not None
                    else None,
                    mail.kind,
                )
        elif mail.compare(constants.MAIL_BUILDING_CONFIG):
            if mail.building_id in self.world.buildings:
                building = self.world.buildings[mail.building_id]
                building.ext.on_client_config(mail)
        elif mail.compare(constants.MAIL_TOGGLE_PAUSE):
            if self.world.paused:
                self.world.unpause()
            else:
                self.world.pause()
            for client in self.clients.values():
                client.conn.mail(constants.MAIL_PAUSE_STATUS, paused=self.world.paused)
        elif mail.compare(constants.MAIL_COPY_CONFIG):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                self.world.copy_config(player, mail.reset)
        elif mail.compare(constants.MAIL_PASTE_CONFIG):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                self.world.paste_config(player)
        elif mail.compare(constants.MAIL_SUBSCRIBE_RESEARCH):
            if mail.client_id in self.world.players:
                player = self.world.players[mail.client_id]
                self.world.research.subscribe_player(player, mail.unsubscribe)

    def force_disconnect(self, client: ClientInterface, timeout=False):
        self.clients.pop(client.id)
        self.world.player_disconnect(client)
        client.conn.mail(constants.MAIL_FORCE_DISCONNECT)
        shared.log(
            f"[S] {'Client timeout' if timeout else 'Kicked client'} (name={client.name}, ID={client.id})"
        )

    def quit(self):
        self.conn.close()

    def run(self):
        while not self.abort:
            if self.client_PID is not None:
                if (
                    god.world.get_ticks() - self.last_client_check
                    >= constants.CLIENT_PID_COOLDOWN * 1000
                ):
                    self.last_client_check = god.world.get_ticks()
                    if not psutil.pid_exists(self.client_PID):
                        shared.log(
                            "[S] Offline client process not found, shutting down\n"
                        )
                        self.abort = True
            while self.mailbox.qsize() > 0:
                self.handle_mail(self.mailbox.get())
            if not self.frozen:
                self.world.frame()
            else:
                self.world.dt = god.dt = 0
            self.conn.frame()
            for client in list(self.clients.values()):
                if (
                    god.world.get_ticks() - client.last_heartbeat
                    >= constants.HEARTBEAT_TIMEOUT * 1000
                ):
                    self.force_disconnect(client, True)
        self.quit()
