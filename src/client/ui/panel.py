import pygame

import shared
from src import constants
from src.client import god
from src.object_data import ResearchNodeOD


class IconButton:
    def __init__(self, icon_name, corner_size, icon_mult=1):
        self.icon_name = icon_name
        self.icon_mult = icon_mult
        self.corner_size = corner_size
        self.hitbox = pygame.Rect()

    def clicked(self, event: pygame.Event):
        return event.button == pygame.BUTTON_LEFT and self.hitbox.collidepoint(
            event.pos
        )

    def render(self, rect: pygame.Rect):
        self.hitbox = rect
        cs = self.corner_size
        hover = rect.collidepoint(god.user_input.mouse_screen)
        if isinstance(self.corner_size, str):
            cs = min(self.hitbox.w, self.hitbox.h) * float(self.corner_size)
        render_panel(
            rect,
            cs,
            outline_alpha=constants.OPAQUE
            if hover
            else constants.UI_PANEL_OUTLINE_ALPHA,
        )
        icon = god.assets.icons_texs[self.icon_name]
        icon.alpha = constants.UI_ICON_BTN_ALPHA
        icon.draw(
            None,
            pygame.Rect(0, 0, rect.w * self.icon_mult, rect.h * self.icon_mult).move_to(
                center=rect.center
            ),
        )
        icon.alpha = constants.OPAQUE
        if hover:
            god.ui.cursor = constants.CURSOR_HOVER


def render_research_node_card(
    rect: pygame.Rect,
    node: ResearchNodeOD | None,
    progress=-1,
    can_hover=False,
    outline_color=None,
):
    hovering = can_hover and rect.collidepoint(god.user_input.mouse_screen)
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
        node.display_name, "white", name_h
    )
    name_tex.draw(
        None,
        name_rect.move_to(midleft=(rect.left + name_h / 2, rect.top + header_h / 2)),
    )
    chip_icon = god.assets.item_texs[node.required_chip.name_id]
    chip_icon.draw(
        None,
        pygame.Rect(0, 0, header_h, header_h).move_to(
            topright=(rect.right - name_h / 4, rect.top)
        ),
    )
    spacing = rect.w * constants.UI_RESEARCH_SPACING_MULT
    item_size = (rect.h - header_h - spacing * 3) / 2
    for i, item in enumerate(node.unlocks):
        img = god.assets.item_texs[item.name_id]
        hitbox = pygame.Rect(
            rect.left + spacing + (item_size + spacing) * i,
            rect.top + header_h + spacing,
            item_size,
            item_size,
        )
        if hitbox.collidepoint(god.user_input.mouse_screen):
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
        progress_text = (
            f"{god.world.research_progress[node]}/{node.cost} | {progress * 100:.2f}%"
        )
        progress_tex, progress_rect = god.assets.font.get_texture_and_rect(
            progress_text, "white", rect.w * constants.UI_RESEARCH_PROGRESS_H_MULT
        )
        progress_tex.draw(
            None,
            progress_rect.move_to(
                midbottom=(rect.left + rect.width * 0.75, rect.bottom - cs - spacing)
            ),
        )
    return hovering


def render_panel_bg(
    rect, corner_size, bg_alpha=constants.UI_PANEL_BG_ALPHA, bg_color="black"
):
    render_panel(rect, corner_size, 0, bg_alpha, 0, bg_color, None)


def render_rect_bg(rect, bg_alpha=constants.UI_PANEL_BG_ALPHA, bg_color="black"):
    white = god.assets.white_tex
    white.alpha = bg_alpha
    white.color = bg_color
    white.draw(None, rect)


def render_panel_outline(
    rect,
    corner_size,
    outline_width=constants.UI_OUTLINE_W,
    outline_alpha=constants.UI_PANEL_OUTLINE_ALPHA,
    outline_color="white",
):
    render_panel(
        rect, corner_size, outline_width, 0, outline_alpha, None, outline_color
    )


def get_corner_bg_texture(cs: float):
    cs = int(cs)
    if f"corner_bg_{cs}" in god.assets.cached_texs:
        bg_tex = god.assets.cached_texs[f"corner_bg_{cs}"]
    else:
        surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
        pygame.draw.aacircle(surf, "white", (cs, cs), cs)
        bg_tex = god.assets.load_tex(surf)
        god.assets.cached_texs[f"corner_bg_{cs}"] = bg_tex
    return bg_tex


def render_panel(
    rect: pygame.FRect | pygame.Rect,
    corner_size,
    outline_width=constants.UI_OUTLINE_W,
    bg_alpha=constants.UI_PANEL_BG_ALPHA,
    outline_alpha=constants.UI_PANEL_OUTLINE_ALPHA,
    bg_color: pygame.typing.ColorLike | None = "black",
    outline_color: pygame.typing.ColorLike | None = "white",
    sharp_bg_corners=None,
):
    if sharp_bg_corners is None:
        sharp_bg_corners = []
    if not isinstance(rect, pygame.Rect | pygame.FRect):
        rect = pygame.FRect(rect)
    cs = corner_size
    if rect.w < cs * 2:
        rect.w = cs * 2
    if rect.h < cs * 2:
        rect.h = cs * 2
    cw = outline_width
    if bg_color is not None and cs > 0:
        bg_tex = get_corner_bg_texture(cs)
        bg_tex.alpha = bg_alpha
        bg_tex.color = bg_color
    else:
        bg_tex = None
    if outline_color is not None and cs > 0:
        if f"corner_outline_{cs}_{cw}" in god.assets.cached_texs:
            outline_tex = god.assets.cached_texs[f"corner_outline_{cs}_{cw}"]
        else:
            surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
            pygame.draw.aacircle(surf, "white", (cs, cs), cs, cw)
            outline_tex = god.assets.load_tex(surf)
            god.assets.cached_texs[f"corner_outline_{cs}_{cw}"] = outline_tex
        outline_tex.alpha = outline_alpha
        outline_tex.color = outline_color
    else:
        outline_tex = None
    white = god.assets.white_tex
    if bg_color is not None:
        white.alpha = bg_alpha
        white.color = bg_color
        white.draw(None, (rect.x + cs, rect.y + cs, rect.w - cs * 2, rect.h - cs * 2))
    for size, a, color in [
        (cs, bg_alpha, bg_color),
        (cw, outline_alpha, outline_color),
    ]:
        if color is None:
            continue
        white.alpha = a
        white.color = color
        if cs * 2 < rect.w:
            white.draw(None, (rect.x + cs, rect.y, rect.w - cs * 2, size))
            white.draw(None, (rect.x + cs, rect.bottom - size, rect.w - cs * 2, size))
        if cs * 2 < rect.h:
            white.draw(None, (rect.x, rect.y + cs, size, rect.h - cs * 2))
            white.draw(None, (rect.right - size, rect.y + cs, size, rect.h - cs * 2))
    for tex in [bg_tex, outline_tex]:
        if tex is None:
            continue
        (tex if tex is outline_tex or "tl" not in sharp_bg_corners else white).draw(
            None, (rect.x, rect.y, cs, cs)
        )
        (tex if tex is outline_tex or "tr" not in sharp_bg_corners else white).draw(
            None, (rect.right - cs, rect.y, cs, cs), flip_x=True
        )
        (tex if tex is outline_tex or "bl" not in sharp_bg_corners else white).draw(
            None, (rect.x, rect.bottom - cs, cs, cs), flip_y=True
        )
        (tex if tex is outline_tex or "br" not in sharp_bg_corners else white).draw(
            None, (rect.right - cs, rect.bottom - cs, cs, cs), flip_x=True, flip_y=True
        )
