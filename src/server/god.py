import typing

if typing.TYPE_CHECKING:
    from src.server.world import World
    from src.server.server import Server

dt: float
world: World = None
server: Server = None
