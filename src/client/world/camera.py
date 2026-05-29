import pygame

from src import constants
from src.client import god


class Camera:
    def __init__(self):
        god.camera = self
        self.zoom = 1.0
        self.pos = pygame.Vector2()

    def frame(self):
        player_to_screen = self.to_screen(god.world.player.pos)
        x_limit = god.windowing.width / constants.CAMERA_LIMIT_DIV
        x_fill = self.size_to_world(god.windowing.width / 2 - x_limit)
        y_limit = god.windowing.height / constants.CAMERA_LIMIT_DIV
        y_fill = self.size_to_world(god.windowing.height / 2 - y_limit)

        if player_to_screen.x <= x_limit:
            self.pos.x = god.world.player.pos.x + x_fill
        if player_to_screen.x >= god.windowing.width - x_limit:
            self.pos.x = god.world.player.pos.x - x_fill
        if player_to_screen.y <= y_limit:
            self.pos.y = god.world.player.pos.y + y_fill
        if player_to_screen.y >= god.windowing.height - y_limit:
            self.pos.y = god.world.player.pos.y - y_fill

    def zoom_event(self, y):
        self.zoom += (y * 0.2) * self.zoom
        self.zoom = pygame.math.clamp(self.zoom, *constants.ZOOM_CLAMP)

    def to_screen(self, world_pos):
        return pygame.Vector2(
            god.windowing.width / 2
            + (world_pos[0] - self.pos.x) * god.unit_px * self.zoom,
            god.windowing.height / 2
            + (world_pos[1] - self.pos.y) * god.unit_px * self.zoom,
        )

    def from_screen(self, screen_pos):
        return pygame.Vector2(
            self.pos.x
            + (screen_pos[0] - god.windowing.width / 2) / (god.unit_px * self.zoom),
            self.pos.y
            + (screen_pos[1] - god.windowing.height / 2) / (god.unit_px * self.zoom),
        )

    def size_to_screen(self, size):
        return size * self.zoom * god.unit_px

    def rect_to_screen(self, rect):
        rect = pygame.FRect(rect)
        return pygame.FRect(
            (
                self.to_screen(rect.topleft),
                (self.size_to_screen(rect.w), self.size_to_screen(rect.h)),
            )
        )

    def size_to_world(self, size):
        return size / self.zoom / god.unit_px
