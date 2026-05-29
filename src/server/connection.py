import json
import socket
import typing

from src import shared
from src import constants

if typing.TYPE_CHECKING:
    from server.server import Server


class ClientConnection:
    def __init__(self, client_id, *args):
        self.client_id = client_id
        self.connected = True

    def mail(self, type_, data): ...


class SocketClientConnection(ClientConnection):
    def __init__(self, client_id, data, server):
        super().__init__(client_id, data, server)
        self.socket: socket.socket = data["socket"]
        self.server: "Server" = server

    def mail(self, type_, **data):
        if not self.connected:
            return
        sock = {"type": type_, "client_id": self.client_id, "data": data}
        sock = json.dumps(sock, separators=constants.JSON_SEPS) + "\n"
        try:
            self.socket.sendall(sock.encode("utf-8"))
        except ConnectionResetError:
            mail = shared.Mail(constants.MAIL_DISCONNECT, self.client_id)
            if mail.valid:
                self.server.mailbox.put(mail)


class ServerConnection:
    def __init__(self, server):
        self.server: "Server" = server

    def frame(self): ...
    def close(self): ...


class SocketServerConnection(ServerConnection):
    def __init__(self, server):
        super().__init__(server)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((constants.SERVER_SOCKET_ADDR, constants.SERVER_SOCKET_PORT))
        self.socket.listen()
        self.socket.setblocking(False)
        shared.log(
            f"[S] Server socket initialized and bound to {constants.SERVER_SOCKET_ADDR}:{constants.SERVER_SOCKET_PORT}"
        )

    def close(self):
        self.socket.close()

    def put_mail(self, type_, client_id, **data):
        mail = shared.Mail(type_, client_id, **data)
        if mail.valid:
            self.server.mailbox.put(mail)

    def frame(self):
        try:
            conn, addr = self.socket.accept()
            conn.setblocking(False)
            self.put_mail(constants.MAIL_CONNECT, None, socket=conn)
        except BlockingIOError:
            ...

        for cid, client in self.server.clients.items():
            try:
                data = client.conn.socket.recv(constants.SOCKET_RECV).decode("utf-8")
                if data:
                    socks = data.split("\n")
                    for sock in socks:
                        if sock.strip():
                            sock = json.loads(sock)
                            self.put_mail(
                                sock["type"], sock["client_id"], **sock["data"]
                            )
                else:
                    self.put_mail(constants.MAIL_DISCONNECT, client.id)
            except BlockingIOError:
                ...
            except ConnectionResetError:
                self.put_mail(constants.MAIL_DISCONNECT, client.id)
