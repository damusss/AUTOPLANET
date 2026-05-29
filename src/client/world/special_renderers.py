import pygame

from src import shared
from src import constants
from src.client import god
from src.client.rendering import SpecialBuildingRenderer
from src.object_data import ItemOD

if constants.NEW_RENDER:
    from pygame._render import Texture
else:
    from pygame._sdl2 import Texture


class SpecialCrafterRenderer(SpecialBuildingRenderer, name_id="crafter"):
    recipe_offset_mult = 28.5 / 32
    recipe_size_mult = 6 / 32
    recipe_outline_size_mult = 0.25 / 32

    item_base_offset_mult = 25 / 32
    animation_size_mult = 14 / 32
    animation_pixel_size = 2

    bar_size_mult = (28 / 32, 6 / 32)
    nozzle_size_mult = (6 / 32, 8 / 32)

    def __init__(self, data):
        super().__init__(data)
        info = self.data.extra
        self.item_surf = self.animation_tex = None
        if info["recipe_uid"] is not None:
            self.item_surf = god.assets.items[ItemOD.get(info["recipe_uid"]).name_id]
            self.animation_tex = Texture.from_surface(
                god.rendering.renderer, self.item_surf
            )
        self.work_start_time = shared.eval_delta(info["work_start_time"])
        self.nozzle_pos = pygame.Vector2()
        self.elapsed_blocks = -1
        self.cur_y = 0

    def render(self, renderer):
        hitbox = pygame.FRect((0, 0), self.data.building_od.size).move_to(
            topleft=(self.data.topleft_x, self.data.topleft_y)
        )
        info = self.data.extra
        if info["recipe_uid"] is None:
            return
        # RECIPE INDICATOR
        recipe = ItemOD.get(info["recipe_uid"])
        recipe_size = hitbox.height * self.recipe_size_mult
        outline_size = hitbox.height * self.recipe_outline_size_mult
        recipe_rect = pygame.FRect(0, 0, recipe_size, recipe_size).move_to(
            center=(
                hitbox.centerx,
                hitbox.top + hitbox.height * self.recipe_offset_mult,
            )
        )
        image = god.assets.item_texs[recipe.name_id]
        image.color = "black"
        for dx, dy in constants.OUTLINE_DIRECTIONS:
            image.draw(
                None,
                god.camera.rect_to_screen(
                    recipe_rect.move(dx * outline_size, dy * outline_size)
                ),
            )
        image.color = "white"
        image.draw(None, god.camera.rect_to_screen(recipe_rect))
        if not info["working"]:
            return
        # ITEM ANIMATION
        complete_time = recipe.create_data.time_s
        elapsed = (god.world.get_ticks() - self.work_start_time) / 1000
        elapsed = elapsed % complete_time
        blocks_count = (self.item_surf.width / self.animation_pixel_size) ** 2
        elapsed_percentage = elapsed / complete_time
        blocks_elapsed = int(elapsed_percentage * blocks_count)
        if blocks_elapsed != self.elapsed_blocks:
            self.elapsed_blocks = blocks_elapsed
            animation_surf = pygame.Surface(self.item_surf.size, pygame.SRCALPHA)
            animation_surf.fill(0)
            cur_y = animation_surf.height - self.animation_pixel_size
            cur_x = 0
            while blocks_elapsed > 0:
                animation_surf.blit(
                    self.item_surf.subsurface(
                        (
                            cur_x,
                            cur_y,
                            self.animation_pixel_size,
                            self.animation_pixel_size,
                        )
                    ),
                    (cur_x, cur_y),
                )
                cur_x += self.animation_pixel_size
                if cur_x >= animation_surf.width:
                    cur_x = 0
                    cur_y -= self.animation_pixel_size
                blocks_elapsed -= 1
            self.cur_y = cur_y
            self.animation_tex.update(animation_surf, ((0, 0), animation_surf.size))
        animation_size = hitbox.width * self.animation_size_mult
        animation_rect = pygame.FRect(0, 0, animation_size, animation_size).move_to(
            midbottom=(
                hitbox.centerx,
                hitbox.top + hitbox.height * self.item_base_offset_mult,
            )
        )
        self.animation_tex.draw(None, god.camera.rect_to_screen(animation_rect))
        # NOZZLE ANIMATION
        bar_tex = god.assets.attachment_texs["crafter_bar"]
        nozzle_tex = god.assets.attachment_texs["crafter_nozzle"]
        bar_size = [hitbox.width * c for c in self.bar_size_mult]
        nozzle_size = [hitbox.width * c for c in self.nozzle_size_mult]
        anim_y_percentage = self.cur_y / self.item_surf.height
        precise_nozzle_pos = (
            animation_rect.left + animation_rect.width * (1 - anim_y_percentage),
            animation_rect.top + animation_rect.height * anim_y_percentage,
        )
        if self.nozzle_pos.magnitude() < constants.ZERO:
            self.nozzle_pos = pygame.Vector2(precise_nozzle_pos)
        else:
            self.nozzle_pos = self.nozzle_pos.lerp(
                precise_nozzle_pos,
                pygame.math.clamp(god.dt * constants.CRAFTER_NOZZLE_LERP_SPEED, 0, 1),
            )
        nozzle_rect = pygame.FRect((0, 0), nozzle_size).move_to(
            midbottom=self.nozzle_pos
        )
        bar_rect = pygame.FRect((0, 0), bar_size).move_to(
            center=(hitbox.centerx, nozzle_rect.centery)
        )
        bar_tex.draw(None, god.camera.rect_to_screen(bar_rect))
        nozzle_tex.draw(None, god.camera.rect_to_screen(nozzle_rect))
