import pygame

from src import shared
from src import mailbox
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui.panel import render_panel, render_panel_bg, render_panel_outline
from src.client.ui.raycast_info import RaycastInfoUI
from src.client.ui.inventory import FloatingSlot
from src.client.ui.interfaces import InventoryInterface, CraftingInterface

if constants.NEW_RENDER:
    from pygame._render import Texture, Renderer
else:
    from pygame._sdl2 import Texture, Renderer


class UIRaycastHit:
    def __init__(
        self,
        item,
        crafting=False,
        amount=0,
        type_=constants.RAYCAST_UI_ITEM,
        filter_=None,
    ):
        self.type = type_
        self.item: ItemOD = item
        self.crafting = crafting
        self.amount = amount
        self.filter = filter_
        self.object_data = self.item


class WorldUI:
    def __init__(self, renderer):
        god.ui = self
        self.ui_raycast = None
        self.inventory_open = False
        self.open_interface = None
        self.renderer = renderer
        self.b = 0
        self.raycast_info = RaycastInfoUI()
        self.inventory = InventoryInterface()
        self.crafting_interface = CraftingInterface()

    def mouse_clicked(self, event: pygame.Event):
        for i, slot in enumerate(god.player.inventory_slots):
            if slot.hitbox.collidepoint(event.pos):
                if self.inventory.floating_slot.source_slot is None:
                    if not slot.empty:
                        if event.button == pygame.BUTTON_LEFT:
                            self.inventory.floating_slot = FloatingSlot(
                                slot, slot.amount
                            )
                        elif event.button == pygame.BUTTON_RIGHT:
                            self.inventory.floating_slot = FloatingSlot(
                                slot,
                                slot.amount // 2 if slot.amount > 1 else slot.amount,
                            )
                else:
                    source = self.inventory.floating_slot.source_slot
                    if event.button == pygame.BUTTON_LEFT:
                        if slot is source:
                            self.inventory.floating_slot = FloatingSlot(None, 0)
                        else:
                            if slot.empty or (
                                source.item == slot.item and not slot.full
                            ):
                                if not slot.empty or slot.check_filter(source.item):
                                    available = source.item.stack_size - slot.amount
                                    to_add = min(
                                        available, self.inventory.floating_slot.amount
                                    )
                                    god.client.conn.mail(
                                        mailbox.MAIL_INVENTORY_ACTION,
                                        action=constants.INVENTORY_ACTION_MOVE,
                                        source={
                                            "container": "player",
                                            "slot": source.i,
                                        },
                                        dest={"container": "player", "slot": i},
                                        amount=to_add,
                                    )
                            else:
                                if slot.check_filter(
                                    source.item
                                ) and source.check_filter(slot.item):
                                    god.client.conn.mail(
                                        mailbox.MAIL_INVENTORY_ACTION,
                                        action=constants.INVENTORY_ACTION_SWAP,
                                        source={
                                            "container": "player",
                                            "slot": source.i,
                                        },
                                        dest={"container": "player", "slot": i},
                                        amount=None,
                                    )
                    elif event.button == pygame.BUTTON_RIGHT:
                        if slot.empty or (source.item == slot.item and not slot.full):
                            if slot is not source:
                                if not slot.empty or slot.check_filter(source.item):
                                    god.client.conn.mail(
                                        mailbox.MAIL_INVENTORY_ACTION,
                                        action=constants.INVENTORY_ACTION_MOVE,
                                        source={
                                            "container": "player",
                                            "slot": source.i,
                                        },
                                        dest={"container": "player", "slot": i},
                                        amount=1,
                                    )
                break

    def render_stats(self):
        box_w = god.windowing.width * constants.UI_BARS_W_MULT
        bar_w = box_w - self.b * 2
        bar_h = bar_w * constants.UI_BARS_H_MULT
        cs = bar_h / 2
        box_h = bar_h * 2 + self.b * 3
        box = pygame.Rect((self.b, self.b, box_w, box_h))
        render_panel_bg(box, cs)
        render_panel_bg(
            (
                box.x + self.b,
                box.y + self.b,
                bar_w * (god.player.health / constants.PLAYER_MAX_HEALTH),
                bar_h,
            ),
            cs,
            bg_alpha=255,
            bg_color=constants.UI_HEALTH_COL,
        )
        render_panel_bg(
            (
                box.x + self.b,
                box.y + self.b * 2 + bar_h,
                bar_w * (god.player.energy / constants.PLAYER_MAX_ENERGY),
                bar_h,
            ),
            cs,
            bg_alpha=255,
            bg_color=constants.UI_ENERGY_COL,
        )
        render_panel_outline(
            (box.x + self.b, box.y + self.b, bar_w, bar_h),
            cs,
            outline_alpha=255,
            outline_color=constants.UI_BARS_OUTLINE_COL,
        )
        render_panel_outline(
            (box.x + self.b, box.y + self.b * 2 + bar_h, bar_w, bar_h),
            cs,
            outline_alpha=255,
            outline_color=constants.UI_BARS_OUTLINE_COL,
        )
        circle = pygame.Rect(box.x + self.b, box.y + self.b, bar_h, bar_h)
        render_panel_bg(circle.inflate(2, 2), cs, 255, constants.UI_BARS_OUTLINE_COL)
        god.assets.health_tex.draw(None, circle.inflate(-4, -4))
        circle = pygame.Rect(
            box.x + self.b, box.y + self.b * 2 + bar_h, bar_h, bar_h
        ).inflate(2, 2)
        render_panel_bg(circle.inflate(2, 2), cs, 255, constants.UI_BARS_OUTLINE_COL)
        god.assets.energy_tex.draw(None, circle.inflate(-4, -4))

        pos_tex, pos_rect = god.assets.font.get_texture_and_rect(
            f"X: {int(god.player.pos.x)} Y: {int(god.player.pos.y)}",
            constants.UI_RAYCAST_INFO_DESCR_COL,
            bar_h,
        )
        pos_tex.draw(None, pos_rect.move_to(topleft=(self.b * 2, box.bottom + self.b)))

    def render(self):
        self.b = god.windowing.width * (constants.UI_BORDER_PERCENT / 100)
        self.render_stats()
        prev_ray = self.ui_raycast
        self.ui_raycast = None
        if self.inventory_open:
            cont, hovering_slot = self.inventory.render(self.b)
            if cont.collidepoint(god.input.mouse_screen):
                self.ui_raycast = constants.UI_RAYCAST_EMPTY
            if self.open_interface is not None:
                self.open_interface.render(
                    self.b, pygame.Rect(cont.x + cont.w / 2, cont.y, cont.w / 2, cont.h)
                )
            if hovering_slot is not None:
                if hovering_slot.empty:
                    if hovering_slot.filter:
                        self.ui_raycast = UIRaycastHit(
                            None,
                            False,
                            0,
                            constants.RAYCAST_UI_SLOT_FILTER,
                            hovering_slot.filter,
                        )
                else:
                    self.ui_raycast = UIRaycastHit(
                        hovering_slot.item,
                        self.open_interface is self.crafting_interface,
                        hovering_slot.amount,
                        constants.RAYCAST_UI_ITEM,
                        hovering_slot.filter,
                    )
        if self.ui_raycast != prev_ray:
            pygame.event.post(
                pygame.Event(
                    pygame.MOUSEBUTTONUP, button=pygame.BUTTON_LEFT, emulated=True
                )
            )
        self.raycast_info.render(self.b)
        if self.inventory.floating_slot.source_slot is not None:
            self.inventory.render_slot(
                god.player.inventory_slots[0].hitbox.move_to(
                    center=god.input.mouse_screen
                ),
                self.inventory.floating_slot,
                None,
                render_bg=False,
            )

    def can_interact_world(self):
        return not self.inventory_open or self.ui_raycast is None

    def toggle_inventory(self):
        if not self.inventory_open:
            self.open_interface = self.crafting_interface
        else:
            self.open_interface = None
            self.inventory.floating_slot = FloatingSlot(None, 0)
        self.inventory_open = not self.inventory_open
