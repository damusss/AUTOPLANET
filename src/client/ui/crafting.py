import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui.panel import render_panel

if constants.NEW_RENDER:
    from pygame._render import Texture, Renderer
else:
    from pygame._sdl2 import Texture, Renderer


class CraftingInterface:
    def __init__(self):
        self.selected_category = constants.CRAFTING_INTERFACE_SECTIONS[0]

    def render(self, b, cont):
        self.b = b
        title_bottom = god.ui.inventory.render_interface_title(
            "Crafting", cont.topleft, cont.w
        )
        bottom = self.render_categories(title_bottom)
        bottom

    def render_categories(self, top): ...
