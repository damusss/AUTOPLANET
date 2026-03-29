import json
import time
import socket

from src import shared
from src import constants


class Connection:
    def __init__(self, client):
        self.client = client
        self.connected = False
        self.last_heartbeat = time.time()

    def mail(self, mail): ...
    def mail_connect(self): ...

    def frame(self):
        self.check_heartbeat()

    def mail_disconnect(self):
        self.mail(constants.MAIL_DISCONNECT)
        self.connected = False

    def connection_accepted(self, mail):
        self.connected = True
        self.client.id = mail.client_id
        self.mail(constants.MAIL_NAME, name=self.client.name)

    def force_disconnected(self):
        self.connected = False
        self.client.id = -1

    def check_heartbeat(self):
        if time.time() - self.last_heartbeat >= constants.HEARTBEAT:
            self.mail(constants.MAIL_HEARTBEAT)
            self.last_heartbeat = time.time()


class SocketConnection(Connection):
    def __init__(self, client):
        super().__init__(client)
        self.socket = None
        self.buffer = ""

    def mail(self, type, **data):
        if not self.connected:
            return
        sock = {"type": type, "client_id": self.client.id, "data": data}
        sock = json.dumps(sock, separators=constants.JSON_SEPS) + "\n"
        try:
            self.socket.sendall(sock.encode("utf-8"))
        except ConnectionResetError:
            self.force_disconnected()

    def mail_connect(self):
        if self.connected:
            return
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((constants.SOCKET_ADDR, constants.SOCKET_PORT))
        self.socket.setblocking(False)

    def mail_disconnect(self):
        super().mail_disconnect()
        self.socket = None

    def force_disconnected(self):
        super().force_disconnected()
        self.socket = None

    def frame(self):
        if self.socket is None:
            return
        try:
            while True:
                data = self.socket.recv(constants.SOCKET_RECV).decode("utf-8")
                if data:
                    while "\n" in data:
                        cur_data, data = data.split("\n", 1)
                        cur_data = self.buffer + cur_data
                        self.buffer = ""
                        sock = json.loads(cur_data)
                        self.client.mailbox.put(
                            shared.Mail(sock["type"], sock["client_id"], **sock["data"])
                        )
                    self.buffer += data
        except BlockingIOError:
            ...
        except ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError:
            self.force_disconnected()

        self.check_heartbeat()
