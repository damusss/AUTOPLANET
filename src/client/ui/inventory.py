import pygame

from src import shared
from src import constants
from src.client import god
from src.client.ui.panel import render_panel


class FloatingSlot:
    def __init__(self, source, amount):
        self.source_slot: shared.Slot = source
        self.amount = amount

    @property
    def item(self):
        return self.source_slot.item

    @property
    def empty(self):
        return (
            self.source_slot is not None
            and self.source_slot.item is None
            or self.amount <= 0
        )


class InventoryInterface:
    def __init__(self):
        self.floating_slot = FloatingSlot(None, 0)
        self.cont = pygame.Rect()
        self.slot_size = 0
        self.right_panning = False
        self.right_panned_slots = set()
        self.left_panning = False
        self.left_panned_slots: list[shared.Slot] = []
        self.left_panned_slot_i = set()
        self.left_pan_amount = 0
        self.left_pan_item = None
        self.pan_source = None
        self.slot_taken_time = pygame.time.get_ticks()

    def start_right_pan(self, slot: shared.Slot):
        self.right_panning = True
        self.right_panned_slots.add(slot.i)
        self.pan_source = self.get_slot_source_slots(slot)

    def end_right_pan(self):
        self.right_panning = False
        self.right_panned_slots = set()
        self.pan_source = None

    def start_left_pan(self, slot: shared.Slot, amount, item):
        self.left_panning = True
        self.left_panned_slots.append(slot)
        self.left_panned_slot_i.add(slot.i)
        self.left_pan_amount = amount
        self.left_pan_item = item
        self.pan_source = self.get_slot_source_slots(slot)

    def end_left_pan(self):
        self.left_panning = False
        self.left_panned_slots = []
        self.left_panned_slot_i = set()
        self.left_pan_amount = 0
        self.left_pan_item = None
        self.pan_source = None

    def right_pan(self):
        if self.pan_source is None:
            self.end_right_pan()
            return
        if (
            self.floating_slot is None
            or self.floating_slot.source_slot is None
            or self.floating_slot.empty
        ):
            self.end_right_pan()
            return
        for i, slot in enumerate(self.pan_source):
            if i in self.right_panned_slots:
                continue
            if slot.hitbox.collidepoint(god.input.mouse_screen):
                source = self.floating_slot.source_slot
                if slot.empty or (source.item == slot.item and not slot.full):
                    if slot is not source:
                        if not slot.empty or slot.check_filter(source.item):
                            self.right_panned_slots.add(i)
                            god.client.conn.mail(
                                constants.MAIL_INVENTORY_ACTION,
                                action=constants.INVENTORY_ACTION_MOVE,
                                source={
                                    "cont": source.cont,
                                    "slot": source.i,
                                },
                                dest={"cont": slot.cont, "slot": i},
                                amount=1,
                            )

    def left_pan(self):
        if self.pan_source is None:
            self.end_left_pan()
            return
        for i, slot in enumerate(self.pan_source):
            if i in self.left_panned_slot_i:
                continue
            if slot.hitbox.collidepoint(god.input.mouse_screen):
                if slot.empty and slot.check_filter(self.left_pan_item):
                    self.left_panned_slot_i.add(i)
                    amount_per_slot_f = self.left_pan_amount / (
                        len(self.left_panned_slots) + 1
                    )
                    amount_per_slot = int(amount_per_slot_f)
                    to_take_from_panned_f = amount_per_slot / len(
                        self.left_panned_slots
                    )
                    to_take_slot_num = len(self.left_panned_slots)
                    if to_take_from_panned_f < 1:
                        to_take_from_panned_f = 1
                        to_take_slot_num = amount_per_slot
                    to_take_from_panned = int(to_take_from_panned_f)
                    amount_taken = 0
                    sorted_panned = sorted(
                        self.left_panned_slots, key=lambda s: s.amount, reverse=True
                    )
                    for s_i, panned_slot in enumerate(sorted_panned):
                        if s_i >= to_take_slot_num:
                            break
                        god.client.conn.mail(
                            constants.MAIL_INVENTORY_ACTION,
                            action=constants.INVENTORY_ACTION_MOVE,
                            source={"cont": panned_slot.cont, "slot": panned_slot.i},
                            dest={"cont": slot.cont, "slot": i},
                            amount=to_take_from_panned,
                        )
                        panned_slot.amount -= to_take_from_panned
                        slot.amount += to_take_from_panned
                        amount_taken += to_take_from_panned
                    if amount_taken < amount_per_slot:
                        sorted_panned = sorted(
                            self.left_panned_slots, key=lambda s: s.amount, reverse=True
                        )
                        for k in range(amount_per_slot - amount_taken):
                            try:
                                panned_slot = sorted_panned[k]
                            except IndexError:
                                continue
                            god.client.conn.mail(
                                constants.MAIL_INVENTORY_ACTION,
                                action=constants.INVENTORY_ACTION_MOVE,
                                source={
                                    "cont": panned_slot.cont,
                                    "slot": panned_slot.i,
                                },
                                dest={"cont": slot.cont, "slot": i},
                                amount=1,
                            )
                            panned_slot.amount -= 1
                            slot.amount += 1
                    self.left_panned_slots.append(slot)
                    if amount_per_slot_f < 1:
                        self.end_left_pan()

    def get_slot_source_slots(self, slot: shared.Slot):
        if slot.cont == "player":
            return god.player.inventory_slots
        if god.ui.open_interface is None:
            return []
        if slot.cont.endswith("in"):
            return god.ui.open_interface.inventories["in"]
        if slot.cont.endswith("out"):
            return god.ui.open_interface.inventories["in"]

    def mouse_clicked(self, event: pygame.Event, interface_slots: list[shared.Slot]):
        for slot in god.player.inventory_slots + interface_slots:
            if not hasattr(slot, "hitbox"):
                continue
            if slot.hitbox.collidepoint(event.pos):
                if self.floating_slot.source_slot is None:
                    if not slot.empty:
                        if event.button == pygame.BUTTON_LEFT:
                            self.floating_slot = FloatingSlot(slot, slot.amount)
                            self.slot_taken_time = pygame.time.get_ticks()
                        elif event.button == pygame.BUTTON_RIGHT:
                            self.floating_slot = FloatingSlot(
                                slot,
                                slot.amount // 2 if slot.amount > 1 else slot.amount,
                            )
                else:
                    source = self.floating_slot.source_slot
                    if event.button == pygame.BUTTON_LEFT:
                        if slot is source:
                            if (
                                pygame.time.get_ticks() - self.slot_taken_time
                                < constants.DOUBLE_CLICK_TIME * 1000
                            ):
                                god.client.conn.mail(
                                    constants.MAIL_INVENTORY_ACTION,
                                    action=constants.INVENTORY_ACTION_CONCENTRATE,
                                    source={"cont": source.cont, "slot": None},
                                    dest={"cont": slot.cont, "slot": slot.i},
                                    amount=None,
                                )
                            else:
                                self.start_left_pan(
                                    slot,
                                    source.amount,
                                    source.item,
                                )
                                self.floating_slot = FloatingSlot(None, 0)
                        else:
                            if slot.empty or (
                                source.item == slot.item and not slot.full
                            ):
                                if not slot.empty or slot.check_filter(source.item):
                                    available = source.item.stack_size - slot.amount
                                    to_add = min(available, self.floating_slot.amount)
                                    if slot.empty:
                                        self.start_left_pan(
                                            slot,
                                            to_add,
                                            source.item,
                                        )
                                    god.client.conn.mail(
                                        constants.MAIL_INVENTORY_ACTION,
                                        action=constants.INVENTORY_ACTION_MOVE,
                                        source={
                                            "cont": source.cont,
                                            "slot": source.i,
                                        },
                                        dest={"cont": slot.cont, "slot": slot.i},
                                        amount=to_add,
                                    )
                            else:
                                if slot.check_filter(
                                    source.item
                                ) and source.check_filter(slot.item):
                                    god.client.conn.mail(
                                        constants.MAIL_INVENTORY_ACTION,
                                        action=constants.INVENTORY_ACTION_SWAP,
                                        source={
                                            "cont": source.cont,
                                            "slot": source.i,
                                        },
                                        dest={"cont": slot.cont, "slot": slot.i},
                                        amount=None,
                                    )
                    elif event.button == pygame.BUTTON_RIGHT:
                        if slot.empty or (source.item == slot.item and not slot.full):
                            if slot is not source:
                                if not slot.empty or slot.check_filter(source.item):
                                    self.start_right_pan(slot)
                                    god.client.conn.mail(
                                        constants.MAIL_INVENTORY_ACTION,
                                        action=constants.INVENTORY_ACTION_MOVE,
                                        source={
                                            "cont": source.cont,
                                            "slot": source.i,
                                        },
                                        dest={"cont": slot.cont, "slot": slot.i},
                                        amount=1,
                                    )
                break
        if not self.cont.collidepoint(event.pos):
            if self.floating_slot is not None and not self.floating_slot.empty:
                amount = 0
                if event.button == pygame.BUTTON_LEFT:
                    amount = self.floating_slot.amount
                elif event.button == pygame.BUTTON_RIGHT:
                    amount = 1
                if amount <= 0:
                    return
                god.client.conn.mail(
                    constants.MAIL_INVENTORY_ACTION,
                    action=constants.INVENTORY_ACTION_DROP,
                    source={
                        "cont": self.floating_slot.source_slot.cont,
                        "slot": self.floating_slot.source_slot.i,
                    },
                    dest={
                        "cont": "right"
                        if event.pos[0] >= self.cont.centerx
                        else "left",
                        "slot": None,
                    },
                    amount=amount,
                )

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
        self.slot_size = slot_size
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
        self.cont = cont
        return cont, hovering_slot

    def render_slot(
        self,
        rect: pygame.Rect,
        slot: "shared.Slot",
        hovering_slot=None,
        empty_icon=None,
        render_bg=True,
        ghost=False,
        outline_color="white",
        storage=True,
        can_hover=True,
        amount_at_two=False,
        image_percentage=1,
    ):
        slot.hitbox = rect
        hovering = rect.collidepoint(god.input.mouse_screen) and render_bg and can_hover
        if render_bg:
            render_panel(
                rect,
                rect.w * constants.UI_SLOT_CORNER_SIZE_MULT,
                2,
                outline_alpha=constants.UI_PANEL_OUTLINE_HOVER_ALPHA
                if hovering
                else constants.UI_PANEL_OUTLINE_ALPHA,
                outline_color=outline_color,
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
            img_rect = pygame.Rect(0, 0, img_h, img_h).move_to(
                center=(
                    rect.centerx,
                    rect.centery
                    - (
                        rect.w
                        * constants.UI_SLOT_IMAGE_OFFSET_Y_MULT
                        * (
                            not slot.empty
                            and slot.item.stack_size > 1
                            and storage
                            and not amount_at_two
                        )
                    ),
                )
            )
            img.draw(
                None,
                img_rect,
            )
            if slot.empty:
                img.alpha = 255
            elif ghost:
                img.alpha = 255
            if image_percentage != 1:
                god.assets.white_tex.color = "black"
                god.assets.white_tex.alpha = constants.UI_SLOT_PROGRESS_ALPHA
                god.assets.white_tex.draw(
                    None,
                    pygame.Rect(
                        img_rect.topleft,
                        (img_rect.w, img_rect.h * (1 - image_percentage)),
                    ),
                )
            if (
                not slot.empty
                and slot.item.stack_size > 1
                and storage
                and (not amount_at_two or slot.amount > 1)
            ):  # and not ghost
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
