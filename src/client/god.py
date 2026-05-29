import typing

if typing.TYPE_CHECKING:
    from src.client.input import Input
    from src.client.assets import Assets
    from src.client.client import Client
    from src.client.windowing import Windowing
    from src.client.ui.screen_ui import ScreenUI
    from src.client.world.player import Player
    from src.client.world.camera import Camera
    from src.client.world.world_state import WorldState
    from src.client.world.world_rendering import WorldRendering

dt: float = 0
unit_px: float = 0
ui: ScreenUI = None
user_input: Input = None
client: Client = None
assets: Assets = None
player: Player = None
camera: Camera = None
world: WorldState = None
windowing: Windowing = None
rendering: WorldRendering = None
