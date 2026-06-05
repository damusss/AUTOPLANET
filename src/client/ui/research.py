import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ResearchNodeOD
from src.client.ui.panel import render_panel, render_rect_bg, get_corner_bg_texture

if constants.NEW_RENDER:
    from pygame._render import Texture
else:
    from pygame._sdl2 import Texture


class ResearchInterface:
    def __init__(self):
        self.b = 0.0
        self.zoom = 1.0
        self.offset = pygame.Vector2()
        self.view_texture: Texture | None = None
        self.renderer = god.windowing.renderer
        self.view_rect: pygame.Rect = pygame.Rect()
        self.total_area: pygame.Rect = pygame.Rect()

    def subscribe(self):
        god.client.conn.mail(constants.MAIL_SUBSCRIBE_RESEARCH, unsubscribe=False)

    def unsubscribe(self):
        god.client.conn.mail(constants.MAIL_SUBSCRIBE_RESEARCH, unsubscribe=True)

    def reset_camera(self):
        self.zoom = 1.0
        self.offset = pygame.Vector2()

    def zoom_event(self, y, mouse_pos: pygame.Vector2):
        prev_zoom = self.zoom
        self.zoom += (y * 0.1) * self.zoom
        self.zoom = pygame.math.clamp(self.zoom, *constants.RESEARCH_ZOOM_CLAMP)
        if self.zoom != prev_zoom:
            zoom_ratio = self.zoom / prev_zoom
            mouse_pos = pygame.Vector2(mouse_pos) - self.view_rect.topleft
            self.offset.x = mouse_pos.x - (mouse_pos.x - self.offset.x) * zoom_ratio
            self.offset.y = mouse_pos.y - (mouse_pos.y - self.offset.y) * zoom_ratio
        self.clamp_offset()

    def drag(self, delta: pygame.Vector2):
        self.offset += delta
        self.clamp_offset()

    def clamp_offset(self):
        diff_x = self.view_rect.width - self.total_area.width
        diff_y = self.view_rect.height - self.total_area.height
        if self.total_area.width > self.view_rect.width:
            self.offset.x = pygame.math.clamp(self.offset.x, diff_x, 0)
        else:
            self.offset.x = pygame.math.clamp(self.offset.x, 0, diff_x)
        if self.total_area.height > self.view_rect.height:
            self.offset.y = pygame.math.clamp(self.offset.y, diff_y, 0)
        else:
            self.offset.y = pygame.math.clamp(self.offset.y, 0, diff_y)

    def render_research_node_card(
        self,
        rect: pygame.Rect,
        node: ResearchNodeOD | None,
        progress=-1.0,
        can_hover=False,
        outline_color=None,
        force_hover=False,
        hover_offset=(0, 0),
    ):
        small = rect.w <= constants.UI_RESEARCH_CARD_SMALL_W
        hovering = force_hover or (
            can_hover
            and rect.move(hover_offset).collidepoint(god.user_input.mouse_screen)
        )
        cs = int(rect.w * constants.UI_RESEARCH_CORNER_SIZE_MULT)
        render_panel(
            rect,
            cs,
            outline_color="white" if outline_color is None else outline_color,
            outline_alpha=constants.UI_PANEL_OUTLINE_HOVER_ALPHA
            if hovering
            else constants.UI_PANEL_OUTLINE_ALPHA,
        )
        if node is None:
            empty_h = rect.w * constants.UI_RESEARCH_EMPTY_H_MULT
            text_tex, text_rect = god.assets.font.get_texture_and_rect(
                "No research node selected", "white", empty_h, rect.w
            )
            text_tex.draw(None, text_rect.move_to(center=rect.center))
            return hovering
        name_h = rect.w * constants.UI_RESEARCH_NAME_H_MULT
        header_h = name_h * 1.1
        name_tex, name_rect = god.assets.font.get_texture_and_rect(
            node.display_name,
            "white",
            name_h * (1 + 0.5 * small),
            rect.w if small else 0,
        )
        name_tex.draw(
            None,
            name_rect.move_to(center=(rect.centerx, rect.centery - cs))
            if small
            else name_rect.move_to(
                midleft=(rect.left + name_h / 2, rect.top + header_h / 2)
            ),
        )
        chip_icon = god.assets.item_texs[node.required_chip.name_id]
        chip_size = header_h * 1.3 if small else header_h
        chip_icon.draw(
            None,
            pygame.Rect(0, 0, chip_size, chip_size).move_to(
                topright=(rect.right - name_h / 4, rect.top)
            ),
        )
        spacing = rect.w * constants.UI_RESEARCH_SPACING_MULT
        if not small:
            item_size = (rect.h - header_h - spacing * 3) / 2
            for i, item in enumerate(node.unlocks):
                img = god.assets.item_texs[item.name_id]
                hitbox = pygame.Rect(
                    rect.left + spacing + (item_size + spacing) * i,
                    rect.top + header_h + spacing,
                    item_size,
                    item_size,
                )
                if hitbox.move(hover_offset).collidepoint(god.user_input.mouse_screen):
                    hovering = shared.Slot(item, 1)
                img.draw(
                    None,
                    hitbox,
                )
        if progress != -1:
            bar_w = rect.w - cs * 2
            bar_h = cs - constants.UI_OUTLINE_W
            corner_bg = get_corner_bg_texture(bar_h)
            corner_bg.alpha = constants.OPAQUE
            corner_bg.color = (
                constants.UI_RESEARCH_PROGRESS_COL
                if progress > 0
                else constants.UI_RESEARCH_PROGRESS_BG_COL
            )
            corner_bg.draw(
                None,
                pygame.Rect(
                    rect.left + constants.UI_OUTLINE_W, rect.bottom - cs, bar_h, bar_h
                ),
                flip_y=True,
            )
            corner_bg.color = (
                constants.UI_RESEARCH_PROGRESS_COL
                if progress >= 1
                else constants.UI_RESEARCH_PROGRESS_BG_COL
            )
            corner_bg.draw(
                None,
                pygame.Rect(rect.right - cs, rect.bottom - cs, bar_h, bar_h),
                flip_x=True,
                flip_y=True,
            )
            render_rect_bg(
                pygame.Rect(
                    rect.left + cs,
                    rect.bottom - cs,
                    bar_w,
                    bar_h,
                ),
                constants.OPAQUE,
                constants.UI_RESEARCH_PROGRESS_BG_COL,
            )
            render_rect_bg(
                pygame.Rect(
                    rect.left + cs,
                    rect.bottom - cs,
                    bar_w * progress,
                    bar_h,
                ),
                constants.OPAQUE,
                constants.UI_RESEARCH_PROGRESS_COL,
            )
            if not small:
                progress_text = f"{god.world.research_progress[node]}/{node.cost} | {progress * 100:.2f}%"
                progress_tex, progress_rect = god.assets.font.get_texture_and_rect(
                    progress_text,
                    "white",
                    rect.w * constants.UI_RESEARCH_PROGRESS_H_MULT,
                )
                progress_tex.draw(
                    None,
                    progress_rect.move_to(
                        midbottom=(
                            rect.left + rect.width * 0.75,
                            rect.bottom - cs - spacing,
                        )
                    ),
                )
        return hovering

    def render(self, b):
        self.b = b
        cont = pygame.Rect(
            0,
            0,
            god.windowing.width * constants.UI_RESEARCH_TREE_W_MULT,
            god.windowing.height * constants.UI_RESEARCH_TREE_H_MULT,
        ).move_to(center=(god.windowing.width / 2, god.windowing.height / 2))
        cs = cont.w * constants.UI_RESEARCH_TREE_CORNER_SIZE_MULT
        render_panel(cont, cs, 2, bg_alpha=constants.UI_PANEL_BG_OPAQUE_ALPHA)
        title_bottom = god.ui.inventory.render_interface_title(
            "Research Tree", cont.topleft, cont.w, 0.4
        )
        view_pad = cs / 2
        self.view_rect = pygame.Rect(
            cont.left + view_pad,
            title_bottom + view_pad,
            cont.width - view_pad * 2,
            (cont.bottom - title_bottom) - view_pad * 2,
        )
        if (
            self.view_texture is None
            or self.view_texture.width != self.view_rect.width
            or self.view_texture.height != self.view_rect.height
        ):
            self.view_texture = Texture(
                self.renderer, self.view_rect.size, 32, target=True
            )
            self.view_texture.blend_mode = pygame.BLENDMODE_BLEND
        self.renderer.target = self.view_texture
        self.renderer.draw_color = 0
        self.renderer.clear()

        hovering_slot = self.render_view()

        self.renderer.target = None
        self.view_texture.draw(None, self.view_rect)
        return cont, hovering_slot

    def render_view(self):
        hovering_slot = None
        card_w = self.view_rect.w * constants.UI_RESEARCH_TREE_CARD_W_MULT * self.zoom
        card_h = card_w * constants.UI_RESEARCH_CARD_H_MULT
        space_x = card_w * constants.UI_RESEARCH_TREE_HORIZ_SPACE_MULT
        space_y = card_w * constants.UI_RESEARCH_TREE_VERT_SPACE_MULT
        total_vertical_height = (
            constants.RESEARCH_TREE_BIGGEST_VERTICAL_AMOUNT * card_h
            + (constants.RESEARCH_TREE_BIGGEST_VERTICAL_AMOUNT - 1) * space_y
        )
        cur_x = self.offset.x
        computed_layout = []
        for horiz_layer in constants.RESEARCH_TREE_LAYOUT:
            layer_vertical_height = (
                len(horiz_layer) * card_h + (len(horiz_layer) - 1) * space_y
            )
            cur_y = (
                self.offset.y + total_vertical_height / 2 - layer_vertical_height / 2
            )
            computed_layer = {}
            for node_name_id, connect_to in horiz_layer:
                node = ResearchNodeOD.get(node_name_id)
                unlocked = node in god.world.researched_nodes
                rect = pygame.Rect(cur_x, cur_y, card_w, card_h)
                hovering_item = self.render_research_node_card(
                    rect,
                    node,
                    god.world.research_progress[node] / node.cost,
                    outline_color=constants.UI_RESEARCH_PROGRESS_COL
                    if unlocked
                    else "white",
                    force_hover=unlocked,
                    hover_offset=self.view_rect.topleft,
                )
                if hovering_item is not None and bool(hovering_item) != hovering_item:
                    hovering_slot = hovering_item
                computed_layer[node.name_id] = rect
                cur_y += card_h + space_y
            computed_layout.append(computed_layer)
            cur_x += card_w + space_x
        self.total_area.width = cur_x - self.offset.x - space_x
        self.total_area.height = total_vertical_height
        for i, horiz_layer in enumerate(constants.RESEARCH_TREE_LAYOUT):
            if i >= len(constants.RESEARCH_TREE_LAYOUT) - 1:
                break
            computed_layer = computed_layout[i]
            next_computed_layer = computed_layout[i + 1]
            for j, (node_name_id, connect_to) in enumerate(horiz_layer):
                start_point = computed_layer[node_name_id].midright
                rects_to_connect = []
                if connect_to == "_next_":
                    rects_to_connect = next_computed_layer.values()
                elif connect_to == "_same_h_":
                    rects_to_connect.append(
                        next_computed_layer[list(next_computed_layer.keys())[j]]
                    )
                else:
                    rects_to_connect.append(next_computed_layer[connect_to])
                self.renderer.draw_color = "white"
                if ResearchNodeOD.get(node_name_id) in god.world.researched_nodes:
                    self.renderer.draw_color = constants.UI_RESEARCH_PROGRESS_COL
                for other_rect in rects_to_connect:
                    self.renderer.draw_line(start_point, other_rect.midleft)
        return hovering_slot
