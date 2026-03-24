import typing

if typing.TYPE_CHECKING:
    from client.ui.ui import WorldUI
    from src.client.input import Input
    from src.client.assets import Assets
    from src.client.client import Client
    from src.client.windowing import Windowing
    from src.client.world.player import Player
    from src.client.world.camera import Camera
    from src.client.world.world_state import WorldState
    from src.client.world.world_rendering import WorldRendering

dt: float = 0
unit_px: float
windowing: Windowing = None
rendering: WorldRendering = None
client: Client = None
world: WorldState = None
assets: Assets = None
player: Player = None
camera: Camera = None
input: Input = None
ui: WorldUI = None
