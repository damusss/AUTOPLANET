import pygame

from src import constants
from src.client import god

if constants.NEW_RENDER:
    from pygame._render import Renderer
else:
    from pygame._sdl2 import Renderer


class Windowing:
    def __init__(self):
        pygame.init()
        god.windowing = self
        size = pygame.display.get_desktop_sizes()[0]
        # size = 1500, 900
        self.window = pygame.Window("Client", size, resizable=True)
        self.renderer = Renderer(self.window, accelerated=True)
        self.renderer.draw_blend_mode = pygame.BLENDMODE_BLEND

    @property
    def size(self):
        return pygame.Vector2(self.window.size)

    @property
    def width(self):
        return self.window.size[0]

    @property
    def height(self):
        return self.window.size[1]

    def frame(self):
        self.renderer.present()
        self.renderer.draw_color = "#000000"
        self.renderer.clear()
        god.unit_px = self.width / constants.UNIT_DIV

    def event(self, e: pygame.Event):
        if e.type == pygame.WINDOWCLOSE and e.window is self.window:
            self.window.destroy()
            pygame.quit()
            return "abort"
