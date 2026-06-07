import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD, VegetationOD, ResearchNodeOD
from src.client.ui.panel import IconButton
from src.client.ui.building import BuildingInterface, ItemSelectionExtension


class StorageInterface(BuildingInterface, name_id="storage"):
    def render(self, b, cont):
        title_bottom = self.render_title(cont, b)
        slot_b = self.b
        slot_size = god.ui.inventory.slot_size
        pad = cont.w * constants.UI_INVENTORY_PADDING_MULT * 2
        slot_i = 0
        hovering_slot = None
        slots = self.inventories["in"]
        for i in range(constants.INVENTORY_ROWS):
            for j in range(constants.INVENTORY_COLS):
                slot_hitbox = pygame.Rect(
                    cont.x
                    + cont.w / 2
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
                hovering_slot = god.ui.inventory.render_slot(
                    slot_hitbox,
                    slots[slot_i],
                    hovering_slot,
                    ghost=(god.ui.inventory.floating_slot.source_slot is slots[slot_i]),
                )
                slot_i += 1
        return hovering_slot


class HopperInterface(BuildingInterface, name_id="hopper"):
    def __init__(self):
        super().__init__()
        self.filter: ItemOD | None = None
        items = sorted(
            sorted(ItemOD.get_iter(), key=lambda item: item.display_name),
            key=lambda item: item.category if item.category is not None else "zzz",
        )
        self.item_selection = ItemSelectionExtension(
            self, items, self.get_config, "Select Filter"
        )

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.filter = ItemOD.get_or(building_data["filter_uid"], None)

    def mouse_clicked(self, event: pygame.Event):
        self.item_selection.mouse_clicked(event)

    def get_config(self, item: ItemOD | None):
        return {"filter_uid": ItemOD.uid_or_none(item)}

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        filter_size = god.ui.inventory.slot_size * 1.5
        slot_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=cont.center)
        filter_rect = pygame.Rect(0, 0, filter_size, filter_size).move_to(
            center=(cont.centerx, cont.centery - cont.h / 4)
        )
        self.item_selection.enter_selection_rect = filter_rect
        slot = self.inventories["in"][0]
        hovering = god.ui.inventory.render_slot(
            slot_rect,
            slot,
            None,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot,
        )
        hovering = god.ui.inventory.render_slot(
            filter_rect, shared.Slot(self.filter, 1), hovering, "lock", storage=False
        )
        return hovering


class BotInterface(BuildingInterface, name_id="bot"):
    def __init__(self):
        super().__init__()
        self.filter: ItemOD | None = None
        items = sorted(
            sorted(ItemOD.get_iter(), key=lambda item: item.display_name),
            key=lambda item: item.category if item.category is not None else "zzz",
        )
        self.item_selection = ItemSelectionExtension(
            self, items, self.get_config, "Select Filter"
        )

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.filter = ItemOD.get_or(building_data["filter_uid"], None)

    def mouse_clicked(self, event: pygame.Event):
        self.item_selection.mouse_clicked(event)

    def get_config(self, item: ItemOD | None):
        return {"filter_uid": ItemOD.uid_or_none(item)}

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        filter_size = god.ui.inventory.slot_size * 1.5
        slot_rect_1 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            midright=(cont.centerx - b, cont.centery)
        )
        slot_rect_2 = pygame.Rect(0, 0, filter_size, filter_size).move_to(
            midleft=(cont.centerx + b, cont.centery)
        )
        filter_rect = pygame.Rect(0, 0, filter_size, filter_size).move_to(
            center=(cont.centerx, cont.centery - cont.h / 4)
        )
        self.item_selection.enter_selection_rect = filter_rect
        slot_1 = self.inventories["in"][0]
        slot_2 = self.inventories["upgrade"][0]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            slot_rect_1,
            slot_1,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_1,
        )
        hovering = god.ui.inventory.render_slot(
            slot_rect_2,
            slot_2,
            hovering,
            "upgrade",
            ghost=god.ui.inventory.floating_slot.source_slot is slot_2,
        )
        hovering = god.ui.inventory.render_slot(
            filter_rect, shared.Slot(self.filter, 1), hovering, "lock", storage=False
        )
        return hovering


class LaboratoryInterface(BuildingInterface, name_id="laboratory"):
    display_recipe = True

    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = 0
        self.contribute_node: ResearchNodeOD | None = None

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.contribute_node = ResearchNodeOD.get_or(
            building_data["contribute_node_uid"], None
        )

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        slot_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            midbottom=cont.center
        )
        slot = self.inventories["in"][0]
        hovering = god.ui.inventory.render_slot(
            slot_rect,
            slot,
            None,
            "microchip",
            ghost=god.ui.inventory.floating_slot.source_slot is slot,
        )
        icon = god.assets.icons_texs["research"]
        icon_size = god.ui.inventory.slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(
            midtop=(cont.centerx, cont.centery + b * 2)
        )
        self.render_icon_progress(
            icon,
            icon_rect,
            self.working,
            self.work_start_time,
            self.contribute_node.required_chip.research_time
            if self.contribute_node is not None
            else 0,
        )
        if self.contribute_node is not None:
            contr_h = cont.w * constants.UI_INVENTORY_TEXT_H_MULT
            contr_tex, contr_rect = god.assets.font.get_texture_and_rect(
                f"Contributing Research: {self.contribute_node.display_name}",
                "white",
                contr_h,
                cont.width - b * 2,
            )
            contr_tex.draw(
                None,
                contr_rect.move_to(
                    center=(cont.centerx, cont.centery + cont.height / 4)
                ),
            )
        return hovering


class ComputerInterface(BuildingInterface, name_id="computer"):
    display_recipe = True

    def __init__(self):
        super().__init__()
        self.active_node: ResearchNodeOD | None = None
        self.available_nodes: list[ResearchNodeOD] = []
        self.working = False
        self.work_start_time = 0
        self.work_advance_amount = 1
        self.research_rect = None
        self.back_btn = IconButton("left_arrow", "0.5", 0.9)
        self.delete_btn = IconButton("delete", "0.5", 0.6)
        self.available_nodes_rects = {}
        self.labs: dict | None = None

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.active_node = ResearchNodeOD.get_or(building_data["active_node_uid"], None)
        self.available_nodes = [
            ResearchNodeOD.get(node_uid)
            for node_uid in building_data["available_nodes_uids"]
        ]
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.work_advance_amount = building_data["work_advance_amount"]
        self.labs = building_data["labs"]
        self.available_nodes_rects = {}

    def render_research_node_selection(self, cont: pygame.Rect):
        bottom = god.ui.inventory.render_interface_title(
            "Select an available Research Node", cont.topleft, cont.w, 0.5
        )
        pad = cont.w * constants.UI_INVENTORY_PADDING_MULT / 2
        b = self.b * 1.5
        available_w = cont.w - pad * 2 - (b * (constants.UI_RESEARCH_CARDS_PER_ROW - 1))
        card_w = available_w / constants.UI_RESEARCH_CARDS_PER_ROW
        card_h = card_w * constants.UI_RESEARCH_CARD_H_MULT
        if len(self.available_nodes) <= 0:
            text_tex, text_rect = god.assets.font.get_texture_and_rect(
                "No research nodes are available.",
                "white",
                card_w * constants.UI_RESEARCH_NAME_H_MULT,
            )
            text_tex.draw(
                None, text_rect.move_to(topleft=(cont.left + pad, bottom + pad))
            )
        x_idx = y_idx = 0
        hovering_slot = None
        for node in self.available_nodes:
            hitbox = pygame.Rect(
                cont.left + pad + (card_w + b) * x_idx,
                bottom + pad + (card_h + b) * y_idx,
                card_w,
                card_h,
            )
            self.available_nodes_rects[node] = hitbox
            ret = god.ui.research.render_research_node_card(
                hitbox, node, can_hover=True
            )
            if ret:
                god.ui.cursor = constants.CURSOR_HOVER
                hovering_slot = ret
            x_idx += 1
            if x_idx >= constants.UI_RESEARCH_CARDS_PER_ROW:
                x_idx = 0
                y_idx += 1
        slot_size = god.ui.inventory.slot_size
        left_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomright=(cont.centerx - b, cont.bottom - b)
        )
        right_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomleft=(cont.centerx + b, cont.bottom - b)
        )
        self.back_btn.render(left_rect)
        self.delete_btn.render(right_rect)
        if hovering_slot and bool(hovering_slot) != hovering_slot:
            return hovering_slot
        return None

    def mouse_clicked(self, event: pygame.Event):
        if event.button != pygame.BUTTON_LEFT:
            return
        if god.ui.overlay_menu_func is not None:
            if self.back_btn.clicked(event):
                god.ui.overlay_menu_func = None
            if self.delete_btn.clicked(event):
                god.ui.overlay_menu_func = None
                god.client.conn.mail(
                    constants.MAIL_BUILDING_CONFIG,
                    building_id=self.building_data.id,
                    active_node_uid=None,
                )
            for node, rect in self.available_nodes_rects.items():
                if rect.collidepoint(event.pos):
                    god.client.conn.mail(
                        constants.MAIL_BUILDING_CONFIG,
                        building_id=self.building_data.id,
                        active_node_uid=node.uid,
                    )
                    god.ui.overlay_menu_func = None
                    break
        else:
            if self.research_rect is None or not self.research_rect.collidepoint(
                event.pos
            ):
                return
            god.ui.overlay_menu_func = self.render_research_node_selection

    def on_exit(self):
        god.ui.research.unsubscribe()

    def on_enter(self):
        god.ui.research.subscribe()

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 1.5
        node_w = cont.w / 1.7
        node_rect = pygame.Rect(
            0, 0, node_w, node_w * constants.UI_RESEARCH_CARD_H_MULT
        ).move_to(center=cont.center)
        progress = -1
        if self.active_node is not None:
            progress = (
                god.world.research_progress[self.active_node] / self.active_node.cost
            )
            if self.working:
                progress += (
                    (god.world.get_ticks() - self.work_start_time)
                    / 1000
                    / self.active_node.required_chip.research_time
                    / self.active_node.cost
                ) * self.work_advance_amount
        hovering_slot = god.ui.research.render_research_node_card(
            node_rect,
            self.active_node,
            progress=progress,
            outline_color="white"
            if self.active_node is None
            else ("white" if self.working else constants.RED_BAD),
        )
        slot = self.inventories["in"][0]
        remote_enabled = (
            self.active_node is not None
            and self.active_node.required_chip != ItemOD.objects.research_chip_1
        )
        if remote_enabled:
            self.research_rect = select_rect = pygame.Rect(
                0, 0, slot_size, slot_size
            ).move_to(midleft=(node_rect.left, cont.centery - cont.h / 4))
            slot_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
                midright=(node_rect.right, cont.centery - cont.h / 4)
            )
        else:
            self.research_rect = select_rect = pygame.Rect(
                0, 0, slot_size, slot_size
            ).move_to(center=(cont.centerx, cont.centery - cont.h / 4))
            slot_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(
                center=(cont.centerx, cont.centery + cont.h / 4)
            )
        if (
            god.ui.inventory.render_slot(
                select_rect,
                shared.Slot(None, 0),
                None,
                "research",
                ghost_empty_icon=False,
            )
            is not None
        ):
            god.ui.cursor = constants.CURSOR_HOVER
        hovering_slot = god.ui.inventory.render_slot(
            slot_rect,
            slot,
            hovering_slot,
            None
            if self.active_node is None
            else (
                "microchip"
                if self.active_node.required_chip == ItemOD.objects.research_chip_1
                else "connection"
            ),
            ghost=god.ui.inventory.floating_slot.source_slot is slot,
            storage=(slot.empty or slot.item != ItemOD.objects.remote_controller),
        )
        if (
            self.active_node is not None
            and self.active_node.required_chip != ItemOD.objects.research_chip_1
            and (slot.amount <= 0 or slot.item != ItemOD.objects.remote_controller)
        ):
            self.render_remote_controller_error(cont, b)
        if remote_enabled:
            self.render_labs_info(cont, b)
        if hovering_slot and bool(hovering_slot) != hovering_slot:
            return hovering_slot
        return None

    def render_labs_info(self, cont: pygame.Rect, b):
        total_h = 0
        to_draw = []
        info_h = cont.w * constants.UI_INVENTORY_TEXT_H_MULT
        title_h = cont.w * constants.UI_INVENTORY_TITLE_H_MULT
        tex, rect = god.assets.font.get_texture_and_rect(
            "Chip Processors:", "white", title_h
        )
        total_h += rect.h
        to_draw.append((tex, rect, b * 2, 0))
        if self.labs is None:
            tex, rect = god.assets.font.get_texture_and_rect(
                "None nearby", constants.RED_BAD, info_h
            )
            total_h += rect.h
            to_draw.append((tex, rect, 0, 0))
        else:
            if self.labs["employed"] > 0:
                tex, rect = god.assets.font.get_texture_and_rect(
                    f"> {self.labs['employed']} employed", constants.GREEN_GOOD, info_h
                )
                total_h += rect.h
                to_draw.append((tex, rect, 0, 0))
            else:
                if self.labs["available"] > 0:
                    tex, rect = god.assets.font.get_texture_and_rect(
                        f"> {self.labs['available']} available",
                        constants.GREEN_GOOD,
                        info_h,
                    )
                    total_h += rect.h
                    to_draw.append((tex, rect, 0, 0))
                if self.labs["busy"] > 0:
                    tex, rect = god.assets.font.get_texture_and_rect(
                        f"> {self.labs['busy']} busy",
                        constants.YELLOW_WARNING,
                        info_h,
                    )
                    total_h += rect.h
                    to_draw.append((tex, rect, 0, 0))
                if self.labs["missing"] > 0:
                    tex, rect = god.assets.font.get_texture_and_rect(
                        f"> {self.labs['missing']} missing requirements",
                        constants.RED_BAD,
                        info_h,
                    )
                    total_h += rect.h
                    to_draw.append((tex, rect, 0, 0))
            tex, rect = god.assets.font.get_texture_and_rect(
                f"{self.labs['nearby']} nearby", "white", info_h
            )
            total_h += rect.h
            to_draw.append((tex, rect, 0, b * 2))
        y = cont.bottom - cont.height / 4.7 - total_h / 2
        for tex, rect, b_post, b_prev in to_draw:
            y += b_prev
            tex.draw(None, rect.move_to(midtop=(cont.centerx, y)))
            y += rect.height + b_post

    def render_remote_controller_error(self, cont: pygame.Rect, b):
        err_h = cont.w * constants.UI_INVENTORY_TEXT_H_MULT
        err_tex, err_rect = god.assets.font.get_texture_and_rect(
            "One remote controller is required.",
            constants.RED_BAD,
            err_h,
            cont.width - b * 2,
        )
        err_tex.draw(None, err_rect.move_to(midbottom=(cont.centerx, cont.bottom - b)))


class MinerInterface(BuildingInterface, name_id="miner"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = 0
        self.work_time = 0

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.work_time = building_data["work_time"]

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        slot_rect_1 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomright=(cont.centerx - b, cont.centery)
        )
        slot_rect_2 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomleft=(cont.centerx + b, cont.centery)
        )
        slot_1 = self.inventories["out"][0]
        slot_2 = self.inventories["out"][1]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            slot_rect_1,
            slot_1,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_1,
        )
        hovering = god.ui.inventory.render_slot(
            slot_rect_2,
            slot_2,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_2,
        )
        icon = god.assets.icons_texs["drill"]
        icon_size = god.ui.inventory.slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(
            midtop=(cont.centerx, cont.centery + b * 2)
        )
        self.render_icon_progress(
            icon, icon_rect, self.working, self.work_start_time, self.work_time
        )
        return hovering


class NyliumHarvesterInterface(BuildingInterface, name_id="nylium_harvester"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = 0
        self.work_time = VegetationOD.objects.nylium_grass.harvester_time_s

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])

    def render(self, b, cont):
        self.render_title(cont, b)
        slot_size = god.ui.inventory.slot_size * 2
        slot_rect_1 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomright=(cont.centerx - b, cont.centery)
        )
        slot_rect_2 = pygame.Rect(0, 0, slot_size, slot_size).move_to(
            bottomleft=(cont.centerx + b, cont.centery)
        )
        slot_1 = self.inventories["out"][0]
        slot_2 = self.inventories["out"][1]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            slot_rect_1,
            slot_1,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_1,
        )
        hovering = god.ui.inventory.render_slot(
            slot_rect_2,
            slot_2,
            hovering,
            None,
            ghost=god.ui.inventory.floating_slot.source_slot is slot_2,
        )
        icon = god.assets.icons_texs["harvest"]
        icon_size = god.ui.inventory.slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(
            midtop=(cont.centerx, cont.centery + b * 2)
        )
        self.render_icon_progress(
            icon, icon_rect, self.working, self.work_start_time, self.work_time
        )
        return hovering


class CrafterInterface(BuildingInterface, name_id="crafter"):
    display_recipe = True

    def __init__(self):
        super().__init__()
        self.recipe: ItemOD | None = None
        self.working = False
        self.work_start_time = 0
        items = sorted(
            sorted(
                filter(
                    lambda item: (
                        item.create_data is not None
                        and item.create_data.type in ["hands", "crafter"]
                    ),
                    ItemOD.get_iter(),
                ),
                key=lambda item: item.display_name,
            ),
            key=lambda item: item.category if item.category is not None else "zzz",
        )
        self.item_selection = ItemSelectionExtension(
            self, items, self.get_config, "Select Recipe"
        )

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.recipe = ItemOD.get_or(building_data["recipe_uid"], None)

    def mouse_clicked(self, event: pygame.Event):
        self.item_selection.mouse_clicked(event)

    def get_config(self, item: ItemOD | None):
        return {"recipe_uid": ItemOD.uid_or_none(item)}

    def render(self, b, cont):
        self.render_title(cont, b)
        left = (cont.centerx - cont.w / 4, cont.centery)
        inv_slot_size = god.ui.inventory.slot_size
        left_w = inv_slot_size * 2 + b
        left_h = (inv_slot_size * constants.CRAFTER_INVENTORY_SIZE / 2) + (
            b * (constants.CRAFTER_INVENTORY_SIZE / 2 - 1)
        )
        cur_top = left[1] - left_h / 2
        hovering = None
        for r in range(int(constants.CRAFTER_INVENTORY_SIZE / 2)):
            cur_left = left[0] - left_w / 2
            for c in range(2):
                slot_rect = pygame.Rect(cur_left, cur_top, inv_slot_size, inv_slot_size)
                slot = self.inventories["in"][r * 2 + c]
                hovering = god.ui.inventory.render_slot(
                    slot_rect,
                    slot,
                    hovering,
                    ghost=(god.ui.inventory.floating_slot.source_slot is slot),
                )
                cur_left += inv_slot_size + b
            cur_top += inv_slot_size + b
        recipe_size = god.ui.inventory.slot_size * 1.2
        recipe_rect = pygame.Rect(0, 0, recipe_size, recipe_size).move_to(
            center=(cont.centerx, cont.centery - cont.h / 4)
        )
        self.item_selection.enter_selection_rect = recipe_rect
        hovering = god.ui.inventory.render_slot(
            recipe_rect,
            shared.Slot(self.recipe, 1),
            hovering,
            "select",
            storage=False,
            ghost_empty_icon=False,
        )
        right = (cont.centerx + cont.w / 4, cont.centery)
        out_slot_size = inv_slot_size * 1.5
        right_rect = pygame.Rect(0, 0, out_slot_size, out_slot_size).move_to(
            center=right
        )
        right_slot = self.inventories["out"][0]
        hovering = god.ui.inventory.render_slot(
            right_rect,
            right_slot,
            hovering,
            ghost=(god.ui.inventory.floating_slot.source_slot is right_slot),
        )
        gear_icon = god.assets.icons_texs["gear"]
        icon_size = inv_slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(center=cont.center)
        self.render_icon_progress(
            gear_icon,
            icon_rect,
            self.working,
            self.work_start_time,
            self.recipe.create_data.time_s if self.recipe is not None else 0,
        )
        return hovering


class FurnaceInterface(BuildingInterface, name_id="furnace"):
    def __init__(self):
        super().__init__()
        self.working = False
        self.work_start_time = 0
        self.work_time = 0

    def refresh_data(self, base_data, building_data):
        self.refresh_inventories_data(base_data, building_data)
        self.working = building_data["working"]
        self.work_start_time = shared.eval_delta(building_data["work_start_time"])
        self.work_time = building_data["work_time"]

    def render(self, b, cont):
        self.render_title(cont, b)
        left = (cont.centerx - cont.w / 4, cont.centery)
        right = (cont.centerx + cont.w / 4, cont.centery)
        slot_size = god.ui.inventory.slot_size * 1.5
        left_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=left)
        right_rect = pygame.Rect(0, 0, slot_size, slot_size).move_to(center=right)
        inv_in, inv_out = self.inventories["in"], self.inventories["out"]
        left_slot = inv_in[0]
        right_slot = inv_out[0]
        hovering = None
        hovering = god.ui.inventory.render_slot(
            left_rect,
            left_slot,
            hovering,
            empty_icon="ore",
            ghost=(god.ui.inventory.floating_slot.source_slot is left_slot),
        )
        hovering = god.ui.inventory.render_slot(
            right_rect,
            right_slot,
            hovering,
            empty_icon="metal",
            ghost=(god.ui.inventory.floating_slot.source_slot is right_slot),
        )
        fire_icon = god.assets.icons_texs["smelt"]
        icon_size = god.ui.inventory.slot_size * 2
        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(center=cont.center)
        self.render_icon_progress(
            fire_icon, icon_rect, self.working, self.work_start_time, self.work_time
        )
        return hovering
