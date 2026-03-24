import pygame

from src import constants
from src.client import god

if constants.NEW_RENDER:
    from pygame._render import Texture, Renderer
else:
    from pygame._sdl2 import Texture, Renderer


class RenderingLayer:
    def render(self, renderer): ...


class TextureRenderingLayer(RenderingLayer):
    def __init__(self, texture, rect, color):
        self.texture = texture
        self.rect = pygame.FRect(rect)
        self.color = color

    def render(self, renderer):
        if self.color is not None:
            self.texture.color = self.color
        self.texture.draw(self.texture.get_rect(), god.camera.rect_to_screen(self.rect))


class AnimatingTextureAtlasRenderingLayer(RenderingLayer):
    def __init__(self, texture_atlas, atlas_dim, frame_speed, rect):
        self.texture_atlas: Texture = texture_atlas
        self.atlas_dim = atlas_dim
        self.frame_speed = frame_speed
        self.rect = rect

        self.frame_index = 0

    def render(self, renderer):
        self.frame_index += self.frame_speed * god.dt
        if self.frame_index >= self.atlas_dim[0] * self.atlas_dim[1]:
            self.frame_index = 0
        row = int(self.frame_index / self.atlas_dim[0])
        col = int(self.frame_index) - row * self.atlas_dim[0]
        size = (
            self.texture_atlas.width / self.atlas_dim[0],
            self.texture_atlas.height / self.atlas_dim[1],
        )
        source = ((col * size[0], row * size[1]), size)
        self.texture_atlas.draw(source, god.camera.rect_to_screen(self.rect))


class MeshRenderingLayer(RenderingLayer):
    def __init__(self, mesh, texture, rect):
        self.mesh = mesh
        self.texture = texture
        self.rect = pygame.FRect(rect)

    def render(self, renderer: Renderer):
        screen_r = god.camera.rect_to_screen(self.rect)
        scale_x = scale_y = screen_r.w / constants.CHUNK_SIZE
        tx, ty = screen_r.topleft
        matrix = [
            scale_x,
            0,
            tx,
            0,
            scale_y,
            ty,
        ]
        renderer.render_geometry(
            self.mesh,
            self.texture,
            transform_matrix=matrix,
        )
