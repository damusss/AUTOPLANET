import json
import socket
import typing

from src import mailbox
from src import constants

if typing.TYPE_CHECKING:
    from server.server import Server


class ClientConnection:
    def __init__(self, client_id, data, server):
        self.client_id = client_id
        self.connected = True

    def mail(self, type, data): ...


class SocketClientConnection(ClientConnection):
    def __init__(self, client_id, data, server):
        super().__init__(client_id, data, server)
        self.socket: socket.socket = data["socket"]
        self.server: "Server" = server

    def mail(self, type, **data):
        if not self.connected:
            return
        sock = {"type": type, "client_id": self.client_id, "data": data}
        sock = json.dumps(sock, separators=constants.JSON_SEPS) + "\n"
        try:
            self.socket.sendall(sock.encode("utf-8"))
        except ConnectionResetError:
            self.server.mailbox.put(
                mailbox.Mail(mailbox.MAIL_DISCONNECT, self.client_id)
            )


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
        self.socket.bind((constants.SOCKET_ADDR, constants.SOCKET_PORT))
        self.socket.listen()
        self.socket.setblocking(False)

    def close(self):
        self.socket.close()

    def put_mail(self, type, client_id, **data):
        self.server.mailbox.put(mailbox.Mail(type, client_id, **data))

    def frame(self):
        try:
            conn, addr = self.socket.accept()
            conn.setblocking(False)
            self.put_mail(mailbox.MAIL_CONNECT, None, socket=conn)
        except BlockingIOError:
            ...

        for cid, client in self.server.clients.items():
            try:
                data = client.conn.socket.recv(constants.SOCKET_RECV).decode("utf-8")
                if data:
                    socks = data.split("\n")
                    for sock in socks:
                        if sock:
                            sock = json.loads(sock)
                            self.put_mail(
                                sock["type"], sock["client_id"], **sock["data"]
                            )
                else:
                    self.put_mail(mailbox.MAIL_DISCONNECT, client.id)
            except BlockingIOError:
                ...
            except ConnectionResetError:
                self.put_mail(mailbox.MAIL_DISCONNECT, client.id)
