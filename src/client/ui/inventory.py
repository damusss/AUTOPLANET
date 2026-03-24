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


class FloatingSlot:
    def __init__(self, source, amount):
        self.source_slot: shared.Slot = source
        self.amount = amount

    @property
    def item(self):
        return self.source_slot.item

    @property
    def empty(self):
        return self.source_slot.item is None or self.amount <= 0


class InventoryInterface:
    def __init__(self):
        self.floating_slot = FloatingSlot(None, 0)

    def render(self, b):
        self.b = b
        cont = pygame.Rect(
            0,
            0,
            god.windowing.width * constants.UI_INVENTORY_W_MULT,
            god.windowing.height * constants.UI_INVENTORY_H_MULT,
        ).move_to(center=(god.windowing.width / 2, god.windowing.height / 2))
        cs = cont.w * constants.UI_INVENTORY_CORNER_SIZE_MULT
        render_panel(cont, cs, 2, bg_alpha=constants.UI_PANEL_BG_OPAQUE_ALPHA)
        god.assets.white_tex.alpha = 255
        god.assets.white_tex.color = "black"
        god.assets.white_tex.draw(None, (cont.centerx - cs, cont.y, cs * 2, 2))
        title_bottom = self.render_interface_title(
            "Inventory", cont.topleft, cont.w / 2
        )
        pad = cont.w * constants.UI_INVENTORY_PADDING_MULT
        slot_b = self.b
        slot_size = (
            cont.w / 2 - pad * 2 - slot_b * (constants.INVENTORY_COLS - 1)
        ) / constants.INVENTORY_COLS
        slot_i = 0
        hovering_slot = None
        for i in range(constants.INVENTORY_ROWS):
            for j in range(constants.INVENTORY_COLS):
                slot_hitbox = pygame.Rect(
                    cont.x
                    + cont.w / 4
                    - (
                        (
                            slot_size * constants.INVENTORY_COLS
                            + slot_b * (constants.INVENTORY_COLS - 1)
                        )
                        / 2
                    )
                    + (slot_size + slot_b) * j,
                    title_bottom + pad + (slot_size + slot_b) * i,
                    slot_size,
                    slot_size,
                )
                hovering_slot = self.render_slot(
                    slot_hitbox,
                    god.player.inventory_slots[slot_i],
                    hovering_slot,
                    ghost=(
                        self.floating_slot.source_slot
                        is god.player.inventory_slots[slot_i]
                    ),
                )
                god.player.inventory_slots[slot_i].hitbox = slot_hitbox
                slot_i += 1
        hand_hitbox = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomleft=(cont.x + pad, cont.bottom - pad)
        )
        hovering_slot = self.render_slot(
            hand_hitbox,
            god.player.inventory_slots[constants.INVENTORY_HAND_I],
            hovering_slot,
            "hand",
            ghost=(
                self.floating_slot.source_slot
                is god.player.inventory_slots[constants.INVENTORY_HAND_I]
            ),
        )
        god.player.inventory_slots[constants.INVENTORY_HAND_I].hitbox = hand_hitbox
        return cont, hovering_slot

    def render_slot(
        self,
        rect: pygame.Rect,
        slot: "shared.Slot",
        hovering_slot,
        empty_icon=None,
        render_bg=True,
        ghost=False,
    ):
        hovering = rect.collidepoint(god.input.mouse_screen) and render_bg
        if render_bg:
            render_panel(
                rect,
                rect.w * constants.UI_SLOT_CORNER_SIZE_MULT,
                2,
                outline_alpha=constants.UI_PANEL_OUTLINE_HOVER_ALPHA
                if hovering
                else constants.UI_PANEL_OUTLINE_ALPHA,
            )
        if not slot.empty or empty_icon is not None:
            img_h = rect.w * constants.UI_SLOT_IMAGE_SIZE_MULT
            img = (
                god.assets.icons_texs[empty_icon]
                if slot.empty
                else god.assets.item_texs[slot.item.name_id]
            )
            if slot.empty:
                img.alpha = int(constants.UI_PANEL_OUTLINE_ALPHA / 4)
            elif ghost:
                img.alpha = constants.UI_SLOT_GHOST_ALPHA
            img.draw(
                None,
                pygame.Rect(0, 0, img_h, img_h).move_to(
                    center=(
                        rect.centerx,
                        rect.centery
                        - (
                            rect.w
                            * constants.UI_SLOT_IMAGE_OFFSET_Y_MULT
                            * (
                                # not ghost and
                                not slot.empty and slot.item.stack_size > 1
                            )
                        ),
                    )
                ),
            )
            if slot.empty:
                img.alpha = 255
            elif ghost:
                img.alpha = 255
            if not slot.empty and slot.item.stack_size > 1:  # and not ghost
                amount_h = rect.w * constants.UI_SLOT_AMOUNT_H_MULT
                amount_tex, amount_rect = god.assets.font.get_texture_and_rect(
                    slot.amount, "white", amount_h
                )
                god.assets.font.font.outline = 1
                amount_outline_tex, amount_outline_rect = (
                    god.assets.font.get_texture_and_rect(
                        slot.amount, "black", amount_h + 2
                    )
                )
                god.assets.font.font.outline = 0
                amount_outline_tex.draw(
                    None,
                    amount_outline_rect.move_to(
                        center=(
                            rect.centerx,
                            rect.bottom - amount_h / (2 if hovering else 8),
                        )
                    ),
                )
                amount_tex.draw(
                    None,
                    amount_rect.move_to(
                        center=(
                            rect.centerx,
                            rect.bottom - amount_h / (2 if hovering else 8),
                        )
                    ),
                )
        if hovering:
            return slot
        else:
            return hovering_slot

    def render_interface_title(self, title, topleft, width):
        title_h = width * constants.UI_INVENTORY_TITLE_H_MULT
        panel_h = title_h * 1.1
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            title, "white", title_h
        )
        panel_rect = pygame.Rect(topleft[0], topleft[1], width, panel_h)
        render_panel(panel_rect, panel_h / 2, 2, bg_alpha=255)
        title_tex.draw(None, title_rect.move_to(center=panel_rect.center))
        return panel_rect.bottom
