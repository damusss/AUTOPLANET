import pygame

from src import shared
from src import mailbox
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui.panel import render_panel_outline, render_panel_bg


class CraftingInterface:
    def __init__(self):
        self.selected_category = 0
        self.category_hitboxes = {}
        self.item_hitboxes = {}

    def mouse_clicked(self, event: pygame.Event):
        for cat, hitbox in self.category_hitboxes.items():
            if hitbox.collidepoint(event.pos):
                self.selected_category = cat
        for item, hitbox in self.item_hitboxes.items():
            if hitbox.collidepoint(event.pos):
                item_od = ItemOD.get(item)
                god.client.conn.mail(mailbox.MAIL_CRAFT_REQUEST, item=item_od.uid)

    def render(self, b, cont: pygame.Rect):
        self.b = b
        self.item_hitboxes = {}
        title_bottom = god.ui.inventory.render_interface_title(
            "Crafting", cont.topleft, cont.w
        )
        bottom = self.render_categories(title_bottom, cont)
        return self.render_rows(bottom, cont.left)

    def render_rows(self, top, left):
        hovering = None
        slot_size = god.ui.inventory.slot_size
        for ri, row in enumerate(
            constants.CRAFTING_INTERFACE_SECTIONS[self.selected_category]["rows"]
        ):
            for i, item in enumerate(row):
                slot_rect = pygame.Rect(
                    left + self.b + i * (slot_size + self.b / 2),
                    top + self.b * 2 + ri * (slot_size + self.b / 2),
                    slot_size,
                    slot_size,
                )
                item_od = ItemOD.get(item)
                status = shared.craft_availability_status(
                    item_od, god.player.count_item
                )
                self.item_hitboxes[item_od.name_id] = slot_rect
                outline_col = constants.CRAFTING_SLOT_COLORS[status.availability]
                hovering = god.ui.inventory.render_slot(
                    slot_rect,
                    shared.Slot(item_od, 1),
                    hovering,
                    outline_color=outline_col,
                    storage=False,
                )
        return hovering

    def render_categories(self, top, cont: pygame.Rect):
        h = god.ui.inventory.slot_size * constants.UI_CRAFTING_CATEOGORIES_H_MULT
        box = pygame.Rect(cont.x + self.b, top + self.b, cont.w - self.b * 2, h)
        cs = box.h * constants.UI_CRAFTING_CATEGORIES_CORNER_SIZE_MULT
        cat_w = box.w / len(constants.CRAFTING_INTERFACE_SECTIONS)
        for i, cat in enumerate(constants.CRAFTING_INTERFACE_SECTIONS):
            hover_rect = pygame.Rect(box.x + cat_w * i, box.y, cat_w, box.h)
            self.category_hitboxes[i] = hover_rect
            if i == self.selected_category:
                render_panel_bg(
                    hover_rect,
                    cs
                    if i in [0, len(constants.CRAFTING_INTERFACE_SECTIONS) - 1]
                    else 0,
                    255,
                )
            icon = god.assets.icons_texs[cat["icon"]]
            hovering = hover_rect.collidepoint(god.input.mouse_screen)
            if hovering:
                god.ui.cursor = constants.CURSOR_HOVER
            icon.alpha = (
                constants.UI_PANEL_OUTLINE_HOVER_ALPHA
                if i == self.selected_category or hovering
                else constants.UI_PANEL_OUTLINE_ALPHA
            )
            icon.draw(
                None,
                pygame.Rect(0, 0, box.h - self.b, box.h - self.b).move_to(
                    center=hover_rect.center
                ),
            )
        render_panel_outline(
            box,
            cs,
        )
        return box.bottom
