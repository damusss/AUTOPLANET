import typing

if typing.TYPE_CHECKING:
    from src.server.world import World
    from src.server.server import Server
    from src.server.research import Research

dt: float
world: World = None
research: Research = None
server: Server = None
