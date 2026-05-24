import os

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import TileOD, ItemOD, BuildingOD, VegetationOD

if constants.NEW_RENDER:
    from pygame._render import Texture
else:
    from pygame._sdl2 import Texture


class FontHandler:
    def __init__(self, renderer):
        self.renderer = renderer
        self.font = pygame.Font("assets/fonts/pixelalien.ttf", constants.FONT_MIN_SIZE)
        self.font.align = pygame.FONT_CENTER
        self.cached_simple_textures = {}

    def resize_wraplength(self, wraplength, text_height):
        return wraplength * (self.font.get_height() / text_height)

    def get_texture(self, text, color=None, wraplength=0, get_line_no=False) -> Texture:
        key = f"{text}_{self.font.outline}"
        if key not in self.cached_simple_textures:
            surf = self.font.render(
                str(text), False, "white", wraplength=int(wraplength)
            )
            size = list(surf.size)
            if size[0] == 0:
                size[0] = 1
            if size[1] == 0:
                size[1] = 1
            tex = Texture.from_surface(self.renderer, surf)
            self.cached_simple_textures[key] = tex
        tex = self.cached_simple_textures[key]
        tex.color = color if color else (255, 255, 255)
        if get_line_no:
            return tex, int(tex.height / self.font.get_height())
        return tex

    def get_texture_and_rect(
        self, text, color, ui_height, ui_wraplength=0
    ) -> tuple[Texture, pygame.Rect]:
        texture, lines = self.get_texture(
            text, color, self.resize_wraplength(ui_wraplength, ui_height), True
        )
        if lines > 1:
            return texture, pygame.Rect(
                0,
                0,
                ui_wraplength
                if ui_wraplength > 0
                else ((texture.width / (texture.height / lines)) * ui_height),
                ui_height * lines,
            )
        ui_width = (texture.width / texture.height) * ui_height
        return texture, pygame.Rect(0, 0, ui_width, ui_height)


class Assets:
    def __init__(self):
        god.assets = self
        self.renderer = god.windowing.renderer
        self.font = FontHandler(self.renderer)

        self.cached_texs = {}

        white = pygame.Surface((10, 10), pygame.SRCALPHA)
        white.fill("white")
        self.white_tex = self.load_tex(white)

        self.tile_not_solid_overlay = pygame.Surface(
            (constants.TILE_PX, constants.TILE_PX), pygame.SRCALPHA
        )
        self.tile_not_solid_overlay.fill(constants.TILE_NOT_SOLID_COLOR_MULT)
        self.placeholder = self.load("placeholder.png")
        self.placeholder_tex = self.load_tex(self.placeholder)

        self.load_particles()
        self.load_big_stars()
        self.load_player()
        self.load_world_ui()
        self.load_ui()
        self.load_tiles()
        self.load_items()
        self.load_icons()
        self.load_vegetation()
        self.load_buildings()
        self.load_building_previews()
        self.load_energy_debug()

    def load_world_ui(self):
        self.raycast_tex = self.load_tex("ui/raycast.png")
        self.raycast_corner_tex = self.load_tex("ui/raycast_corner.png")
        self.raycast_tex.alpha = self.raycast_corner_tex.alpha = int(0.8 * 255)

        self.break_anim_texs = []
        for i in range(len(os.listdir("assets/images/ui/break_animation"))):
            surf = self.load(f"ui/break_animation/{i}.png")
            surf.fill("black", special_flags=pygame.BLEND_RGB_MULT)
            mask = pygame.mask.from_surface(surf)
            surf = mask.to_surface(None, setcolor="white", unsetcolor=(0, 0, 0, 0))
            self.break_anim_texs.append(self.load_tex(surf))

    def load_ui(self):
        self.energy_tex = self.load_tex("ui/energy.png")
        self.health_tex = self.load_tex("ui/health.png")

    def load_particles(self):
        self.particle = self.load("particle.png")
        self.particle_tex = self.load_tex(self.particle)

        star = pygame.transform.smoothscale(self.particle, (10, 10))
        self.star_tex = self.load_tex(star)

        self.light_tex = self.load_tex(self.particle)
        self.light_tex.blend_mode = pygame.BLENDMODE_ADD

        self.dust_particle_tex = self.load_tex(self.particle)
        self.dust_star_particle_tex = self.load_tex(self.particle)
        self.dust_black_hole_particle_tex = self.load_tex(self.particle)
        self.dust_particle_tex.alpha = int(0.15 * 255)
        self.dust_star_particle_tex.alpha = int(0.3 * 255)
        self.dust_black_hole_particle_tex.alpha = int(0.8 * 255)

    def load_big_stars(
        self,
    ):
        self.black_hole_tex = self.load_tex("stars/black_hole.png")
        self.big_star_texs = []
        for i in range(8):
            self.big_star_texs.append(self.load_tex(f"stars/{i}.png"))

    def load_player(self):
        self.player_idle_texs: list[Texture] = []
        self.player_run_texs: list[Texture] = []
        for name in ["idleshort", "idlehigh"]:
            self.player_idle_texs.append(self.load_tex(f"player/idle/{name}.png"))
        for name in ["righthigh", "leftshort", "rightshort", "lefthigh"]:
            self.player_run_texs.append(self.load_tex(f"player/run/{name}.png"))

    def load_tiles(self):
        self.tiles: dict[str, pygame.Surface] = {}
        self.tile_texs: dict[str, Texture] = {}
        placeholder = pygame.transform.smoothscale(
            self.placeholder.convert(32), (constants.TILE_PX, constants.TILE_PX)
        )
        for tile in TileOD.get_all().keys():
            try:
                surf = self.load(f"tiles/{tile}.png")
                self.tiles[tile] = surf
                self.tile_texs[tile] = self.load_tex(surf)
            except FileNotFoundError:
                shared.log(f"Missing image 'tiles/{tile}.png'")
                self.tile_texs[tile] = self.placeholder_tex
                self.tiles[tile] = placeholder

    def load_vegetation(self):
        self.vegetation: dict[str, pygame.Surface] = {}
        self.vegetation_texs: dict[str, Texture] = {}
        for vegetation in VegetationOD.get_all().keys():
            try:
                surf = self.load(f"vegetation/{vegetation}.png")
                self.vegetation[vegetation] = surf
                self.vegetation_texs[vegetation] = self.load_tex(surf)
            except FileNotFoundError:
                shared.log(f"Missing image 'vegetation/{vegetation}.png'")
                self.vegetation_texs[vegetation] = self.placeholder_tex

    def load_buildings(self):
        self.buildings: dict[str, pygame.Surface] = {}
        self.building_texs: dict[str, Texture] = {}
        for building in BuildingOD.get_list():
            try:
                surf = self.load(f"items/{building.name_id}.png")
                self.buildings[building.name_id] = surf
                self.building_texs[building.name_id] = self.load_tex(surf)
            except FileNotFoundError:
                self.buildings[building.name_id] = pygame.transform.scale(
                    self.placeholder,
                    (
                        building.size[0] * constants.TILE_PX,
                        building.size[1] * constants.TILE_PX,
                    ),
                )
                self.building_texs[building.name_id] = self.placeholder_tex
            for state in building.states.values():
                if state.default_image:
                    continue
                try:
                    surf = self.load(f"items/states/{state.image_name}.png")
                    self.buildings[state.image_name] = surf
                    self.building_texs[state.image_name] = self.load_tex(surf)
                except FileNotFoundError:
                    shared.log(
                        f"Missing building state image 'items/states/{state.image_name}.png'"
                    )
                    self.buildings[state.image_name] = pygame.transform.scale(
                        self.placeholder,
                        (
                            building.size[0] * constants.TILE_PX,
                            building.size[1] * constants.TILE_PX,
                        ),
                    )
                    self.building_texs[state.image_name] = self.placeholder_tex

    def load_items(self):
        self.item_texs: dict[str, Texture] = {}
        self.drop_inflate_percentages: dict[str, float] = {}
        for item in ItemOD.get_all().keys():
            try:
                surf = self.load(f"items/{item}.png")
                self.item_texs[item] = self.load_tex(surf)
                mask = pygame.mask.from_surface(surf)
                bounding = mask.get_bounding_rects()[0]
                self.drop_inflate_percentages[item] = surf.height / bounding.h
            except FileNotFoundError:
                shared.log(f"Missing image 'items/{item}.png'")
                self.item_texs[item] = self.placeholder_tex

    def load_building_previews(self):
        self.building_preview_texs: dict[str, Texture] = {}
        for building in BuildingOD.get_all().keys():
            try:
                surf = self.load(f"items/{building}.png")
                surf = pygame.transform.grayscale(surf)
                self.building_preview_texs[building] = self.load_tex(surf)
            except FileNotFoundError:
                self.building_preview_texs[building] = self.placeholder_tex

    def load_icons(self):
        self.icons_texs: dict[str, Texture] = {}
        for file in os.listdir("assets/images/icons"):
            name, ext = file.split(".")
            if ext == "svg":
                surf = pygame.image.load_sized_svg(
                    f"assets/images/icons/{file}",
                    (constants.ICON_SVG_SIZE, constants.ICON_SVG_SIZE),
                )
                self.icons_texs[name] = self.load_tex(surf)
            else:
                self.icons_texs[name] = self.load_tex(f"icons/{file}")

    def load_energy_debug(self):
        plant_r = BuildingOD.objects.energy_plant.energy_radius
        transmitter_r = BuildingOD.objects.energy_transmitter.energy_radius
        plant_surf = pygame.Surface((plant_r * 2, plant_r * 2), pygame.SRCALPHA)
        transmitter_surf = pygame.Surface(
            (transmitter_r * 2, transmitter_r * 2), pygame.SRCALPHA
        )
        pygame.draw.circle(plant_surf, "white", (plant_r, plant_r), plant_r)
        pygame.draw.circle(
            transmitter_surf, "white", (transmitter_r, transmitter_r), transmitter_r
        )
        self.energy_plant_debug_tex = self.load_tex(plant_surf)
        self.energy_transmitter_debug_tex = self.load_tex(transmitter_surf)

        color = pygame.Color(constants.ENERGY_DEBUG_COLOR)
        color.a = constants.ENERGY_DEBUG_ALPHA
        self.energy_plant_debug_tex.color = self.energy_transmitter_debug_tex.color = (
            color
        )

    def load_tex(self, surf_or_file):
        if isinstance(surf_or_file, pygame.Surface):
            return Texture.from_surface(self.renderer, surf_or_file)
        return Texture.from_surface(self.renderer, self.load(surf_or_file))

    def load(self, file):
        return pygame.image.load(f"assets/images/{file}")
