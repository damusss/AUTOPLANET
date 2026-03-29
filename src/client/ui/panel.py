import pygame

from src import constants
from src.client import god


def render_panel_bg(
    rect, corner_size, bg_alpha=constants.UI_PANEL_BG_ALPHA, bg_color="black"
):
    return render_panel(rect, corner_size, 0, bg_alpha, 0, bg_color, None)


def render_panel_outline(
    rect,
    corner_size,
    outline_width=2,
    outline_alpha=constants.UI_PANEL_OUTLINE_ALPHA,
    outline_color="white",
):
    return render_panel(
        rect, corner_size, outline_width, 0, outline_alpha, None, outline_color
    )


def render_panel(
    rect: pygame.FRect,
    corner_size,
    outline_width=2,
    bg_alpha=constants.UI_PANEL_BG_ALPHA,
    outline_alpha=constants.UI_PANEL_OUTLINE_ALPHA,
    bg_color="black",
    outline_color="white",
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
        if f"corner_bg_{cs}" in god.assets.cached_texs:
            bg_tex = god.assets.cached_texs[f"corner_bg_{cs}"]
        else:
            surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
            pygame.draw.aacircle(surf, "white", (cs, cs), cs)
            bg_tex = god.assets.load_tex(surf)
            god.assets.cached_texs[f"corner_bg_{cs}"] = bg_tex
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
