import typing

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD, TileOD, BuildingOD
from src.client.ui.panel import render_panel_bg

if typing.TYPE_CHECKING:
    from src.client.ui.screen_ui import UIRaycastHit


class RaycastInfoUI:
    def render(self, border):
        self.b = border
        raycast = god.player.raycast
        if god.ui.ui_raycast is not None and (
            god.ui.inventory_open or god.ui.ui_raycast != constants.UI_RAYCAST_EMPTY
        ):
            raycast = god.ui.ui_raycast
        col_w = god.windowing.width * constants.UI_RAYCAST_INFO_W_MULT
        cs = col_w * constants.UI_RAYCAST_INFO_CORNER_SIZE_MULT
        if (
            raycast is None
            or raycast is constants.UI_RAYCAST_EMPTY
            or raycast.type == constants.RAYCAST_EMPTY
        ):
            self.try_render_building_status(0, col_w, cs)
            return 0
        bottom = self.try_render_building_status(0, col_w, cs)
        if raycast.object_data is not None:
            bottom = self.render_main(bottom, raycast, col_w, cs, self.b, self.b * 2)
        if raycast.type == constants.RAYCAST_TILE:
            if len(raycast.object_data.item_drop) > 0:
                bottom = self.render_drops(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            bottom = self.render_object_pos(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )
        elif raycast.type == constants.RAYCAST_DROP:
            self.render_drop_amount(bottom, raycast, col_w, cs, self.b, self.b * 2)
        elif raycast.type == constants.RAYCAST_BUILDING:
            if raycast.object_data.need_energy or raycast.object_data.interface:
                bottom = self.render_building_interaction(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            if isinstance(raycast.data[-1], list):
                bottom = self.render_extra_building_data(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            bottom = self.render_object_pos(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )
        elif raycast.type == constants.RAYCAST_VEGETATION:
            if len(raycast.object_data.item_drop) > 0:
                bottom = self.render_drops(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            bottom = self.render_object_pos(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )
        elif raycast.type == constants.RAYCAST_UI_ITEM:
            if raycast.filter:
                bottom = self.render_slot_filter(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            if raycast.crafting:
                if raycast.item.create_data is not None:
                    bottom = self.render_item_recipe(
                        bottom, raycast, col_w, cs, self.b, self.b * 2
                    )
                    if raycast.item.create_data.type != constants.CREATE_HANDS:
                        bottom = self.render_item_create_in(
                            bottom, raycast, col_w, cs, self.b, self.b * 2
                        )
            else:
                if god.ui.overlay_menu_func is None:
                    bottom = self.render_item_amount(
                        bottom, raycast, col_w, cs, self.b, self.b * 2
                    )
            if raycast.item.smelt_result is not None:
                bottom = self.render_item_smelt_result(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            building = raycast.item.building
            if building is not None:
                if len(building.floor_whitelist) > 0:
                    bottom = self.render_building_floor_whitelist(
                        bottom, building, col_w, cs, self.b, self.b * 2
                    )
        elif raycast.type == constants.RAYCAST_UI_SLOT_FILTER:
            bottom = self.render_slot_filter(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )
        return bottom

    def try_render_building_status(self, top, col_w, cs):
        if god.player.building_preview is not None:
            if len(god.player.building_preview.floor_whitelist) > 0:
                top = self.render_building_floor_whitelist(
                    top, god.player.building_preview, col_w, cs, self.b, self.b * 2
                )
            if god.player.building_available != constants.BUILDING_STATUS_AVAILABLE:
                top = self.render_building_status(top, col_w, cs, self.b, self.b * 2)
        return top

    def render_slot_filter(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        title_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        text = "Unknown Slot Filter"
        if raycast.filter == constants.INVENTORY_FILTER_SENTINEL_SHORTCUT:
            text = "Shortcut slot."
        elif raycast.filter[0] == constants.INVENTORY_FILTER_CATEGORY:
            text = f"Slot Category Whitelist: {', '.join([constants.ITEM_CATEGORY_NAMES[cat] for cat in raycast.filter[1]])}"
        elif raycast.filter[0] == constants.INVENTORY_FILTER_READONLY:
            text = "Slot is read-only."
        elif raycast.filter[0] == constants.INVENTORY_FILTER_WHITELIST:
            # TEMPORARY
            text = f"Slot Item Whitelist: {', '.join([ItemOD.get(name).display_name for name in raycast.filter[1]])}"
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            text, "white", title_h, content_w
        )
        box = pygame.Rect(
            god.windowing.width - bb - col_w, top + bb, col_w, b * 2 + title_rect.h
        )
        render_panel_bg(box, cs)
        title_tex.draw(None, title_rect.move_to(center=box.center))
        return box.bottom

    def render_item_recipe(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        subtitle_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        item_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        item_name_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        subtitle_tex, subtitle_rect = god.assets.font.get_texture_and_rect(
            "Recipe", "white", subtitle_h
        )
        box = pygame.Rect(
            god.windowing.width - bb - col_w,
            top + bb,
            col_w,
            bb + subtitle_rect.h + b,
        )

        subtitle_rect = subtitle_rect.move_to(midtop=(box.centerx, box.top + bb))
        to_draw: list = [(subtitle_tex, subtitle_rect, None)]

        for item_od, amount in raycast.item.create_data.recipe:
            item_count = god.player.count_item(item_od)
            amount_col = "white"
            if item_count >= amount:
                amount_col = constants.GREEN_GOOD
            else:
                status = shared.craft_availability_status(
                    item_od, god.player.count_item, amount - item_count
                )
                if status.availability in [
                    constants.CRAFT_READY,
                    constants.CRAFT_READY_SUBSTEP,
                ]:
                    amount_col = constants.CRAFTING_SLOT_COLORS[
                        constants.CRAFT_READY_SUBSTEP
                    ]
                elif status.availability == constants.CRAFT_UNAVAILABLE:
                    amount_col = constants.RED_BAD
                elif status.availability == constants.CRAFT_NOT_READY:
                    amount_col = constants.CRAFTING_SLOT_COLORS[
                        constants.CRAFT_NOT_READY
                    ]
            amount_txt = f"{item_count}/{amount}"
            amount_tex, amount_rect = god.assets.font.get_texture_and_rect(
                amount_txt, amount_col, item_name_h
            )
            name_tex, name_rect = god.assets.font.get_texture_and_rect(
                item_od.display_name,
                "white",
                item_name_h,
                content_w - item_h - amount_rect.w,
            )
            row_rect = pygame.Rect(
                box.left + b, box.bottom, content_w, max(item_h, name_rect.h)
            )

            image_tex = god.assets.item_texs[item_od.name_id]
            to_draw.append(
                (
                    image_tex,
                    pygame.Rect(0, 0, item_h, item_h).move_to(
                        midright=row_rect.midright
                    ),
                    None,
                )
            )
            to_draw.append(
                (amount_tex, amount_rect.move_to(midleft=row_rect.midleft), amount_col)
            )
            to_draw.append((name_tex, name_rect.move_to(center=row_rect.center), None))
            box.h += row_rect.h + b

        render_panel_bg(box, cs)
        for img, rect, col in to_draw:
            if col:
                img.color = col
            img.draw(None, rect)

        return box.bottom

    def render_item_smelt_result(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        subtitle_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        item_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        item_name_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        res_tex, res_rect = god.assets.font.get_texture_and_rect(
            "Smelted", "white", subtitle_h
        )
        place_tex, place_rect = god.assets.font.get_texture_and_rect(
            "Smelt In (min.)", "white", subtitle_h
        )
        box = pygame.Rect(god.windowing.width - col_w - bb, top + bb, col_w, bb)
        to_draw = []
        res_rect = res_rect.move_to(midtop=box.midbottom)
        box.h += res_rect.h + bb
        to_draw.append((res_tex, res_rect))
        name_tex, name_rect = god.assets.font.get_texture_and_rect(
            raycast.item.smelt_result.display_name, "white", item_name_h
        )
        image_tex = god.assets.item_texs[raycast.item.smelt_result.name_id]
        to_draw.append(
            (
                image_tex,
                pygame.Rect(0, 0, item_h, item_h).move_to(
                    topright=(box.right - b, box.bottom)
                ),
            )
        )
        to_draw.append(
            (
                name_tex,
                name_rect.move_to(center=(box.centerx, box.bottom + item_h / 2)),
            )
        )
        box.h += item_h + b
        place_rect = place_rect.move_to(midtop=box.midbottom)
        box.h += place_rect.h + bb
        to_draw.append((place_tex, place_rect))
        place_od = ItemOD.get(raycast.item.smelt_result.create_data.type)
        name_tex, name_rect = god.assets.font.get_texture_and_rect(
            place_od.display_name, "white", item_name_h
        )
        image_tex = god.assets.item_texs[place_od.name_id]
        to_draw.append(
            (
                image_tex,
                pygame.Rect(0, 0, item_h, item_h).move_to(
                    topright=(box.right - b, box.bottom)
                ),
            )
        )
        to_draw.append(
            (
                name_tex,
                name_rect.move_to(center=(box.centerx, box.bottom + item_h / 2)),
            )
        )
        box.h += item_h + b
        render_panel_bg(box, cs)
        for img, rect in to_draw:
            img.draw(None, rect)
        return box.bottom

    def render_item_create_in(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        subtitle_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        item_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        item_name_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        subtitle_tex, subtitle_rect = god.assets.font.get_texture_and_rect(
            "Create In (min.)", "white", subtitle_h
        )
        box = pygame.Rect(god.windowing.width - col_w - bb, top + bb, col_w, bb)
        to_draw = []
        subtitle_rect = subtitle_rect.move_to(midtop=box.midbottom)
        box.h += subtitle_rect.h + b
        to_draw.append((subtitle_tex, subtitle_rect))
        building_item_od = ItemOD.get(raycast.item.create_data.type)
        name_tex, name_rect = god.assets.font.get_texture_and_rect(
            building_item_od.display_name, "white", item_name_h
        )
        image_tex = god.assets.item_texs[building_item_od.name_id]
        to_draw.append(
            (
                image_tex,
                pygame.Rect(0, 0, item_h, item_h).move_to(
                    topright=(box.right - b, box.bottom)
                ),
            )
        )
        to_draw.append(
            (
                name_tex,
                name_rect.move_to(center=(box.centerx, box.bottom + item_h / 2)),
            )
        )
        box.h += item_h + b
        render_panel_bg(box, cs)
        for img, rect in to_draw:
            img.draw(None, rect)
        return box.bottom

    def render_item_amount(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        text_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        shortcut = raycast.filter == constants.INVENTORY_FILTER_SENTINEL_SHORTCUT
        text_tex, text_rect = god.assets.font.get_texture_and_rect(
            f"Inventory: {raycast.amount if shortcut else god.player.count_item(raycast.item)}",
            "white",
            text_h,
        )
        text2_tex, text2_rect = god.assets.font.get_texture_and_rect(
            (
                "Left click to clear shortcut."
                if god.ui.inventory_open
                else "Left click to hold."
            )
            if shortcut
            else f"Slot: {raycast.amount}/{raycast.item.stack_size}",
            constants.UI_INFO_DESCR_COL,
            text_h,
            content_w,
        )
        box = pygame.Rect(
            god.windowing.width - bb - col_w,
            top + bb,
            col_w,
            b * 2 + text_rect.h + text2_rect.h,
        )
        render_panel_bg(box, cs)
        text_tex.draw(None, text_rect.move_to(midtop=(box.centerx, box.top + b)))
        text2_tex.draw(
            None, text2_rect.move_to(midtop=(box.centerx, box.top + b + text_h))
        )
        return box.bottom

    def render_building_status(self, top, col_w, cs, bb, b):
        content_w = col_w - b * 2
        title_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        status_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            "Building Status", "white", title_h, content_w
        )
        status = constants.BUILDING_STATUS_MESSAGES[god.player.building_available]
        if god.player.building_available == constants.BUILDING_STATUS_WRONG_ALTITUDE:
            status = status.replace(
                "<r1>", god.player.building_preview.altitude_range[0]
            ).replace("<r2>", god.player.building_preview.altitude_range[1])
        elif (
            god.player.building_available
            == constants.BUILDING_STATUS_MISSING_VEGETATION
            and god.player.building_preview.vegetation_requirement is not None
        ):
            status = status.replace(
                "<vegetation>",
                god.player.building_preview.vegetation_requirement.display_name,
            )
        status_tex, status_rect = god.assets.font.get_texture_and_rect(
            status, constants.RED_BAD, status_h, content_w
        )
        box = pygame.Rect(
            god.windowing.width - col_w - bb,
            top + bb,
            col_w,
            bb + title_rect.h + b * 2 + status_rect.h,
        )
        render_panel_bg(box, cs)
        title_rect = title_rect.move_to(midtop=(box.centerx, box.top + bb))
        title_tex.draw(None, title_rect)
        status_tex.draw(
            None, status_rect.move_to(midtop=(box.centerx, title_rect.bottom + b))
        )
        return box.bottom

    def render_building_floor_whitelist(
        self, top, building_od: BuildingOD, col_w, cs, bb, b
    ):
        content_w = col_w - b * 2
        subtitle_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        subtitle_tex, subtitle_rect = god.assets.font.get_texture_and_rect(
            "Place On", "white", subtitle_h
        )
        floor_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        floor_name_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        box = pygame.Rect(
            god.windowing.width - bb - col_w, top + bb, col_w, bb + subtitle_rect.h
        )
        subtitle_rect = subtitle_rect.move_to(midbottom=box.midbottom)
        box.h += b
        to_draw = [(subtitle_tex, subtitle_rect)]
        for floor_od in building_od.floor_whitelist:
            floor_tex, floor_rect = god.assets.font.get_texture_and_rect(
                floor_od.display_name, "white", floor_name_h, content_w - floor_h
            )
            img = (
                god.assets.tile_texs
                if isinstance(floor_od, TileOD)
                else god.assets.item_texs
            )[floor_od.name_id]
            h = max(floor_rect.h, floor_h)
            box.h += h
            to_draw.append(
                (
                    floor_tex,
                    floor_rect.move_to(center=(box.centerx, box.bottom - h / 2)),
                )
            )
            to_draw.append(
                (
                    img,
                    pygame.Rect(0, 0, floor_h, floor_h).move_to(
                        midright=(box.right - b, box.bottom - h / 2)
                    ),
                )
            )
            box.h += b
        if building_od.vegetation_requirement is not None:
            box.h += b * 2
            subtitle_tex, subtitle_rect = god.assets.font.get_texture_and_rect(
                "Requires", "white", subtitle_h
            )
            subtitle_rect = subtitle_rect.move_to(midbottom=box.midbottom)
            box.h += b * 2
            veg_od = building_od.vegetation_requirement
            to_draw.append((subtitle_tex, subtitle_rect))
            veg_tex, veg_rect = god.assets.font.get_texture_and_rect(
                veg_od.display_name, "white", floor_name_h, content_w - floor_h
            )
            img = god.assets.vegetation_texs[veg_od.name_id]
            h = max(floor_rect.h, floor_h)
            box.h += h
            to_draw.append(
                (
                    veg_tex,
                    veg_rect.move_to(center=(box.centerx, box.bottom - h / 2)),
                )
            )
            to_draw.append(
                (
                    img,
                    pygame.Rect(0, 0, floor_h, floor_h).move_to(
                        midright=(box.right - b, box.bottom - h / 2)
                    ),
                )
            )
            box.h += b
        render_panel_bg(box, cs)
        for tex, rect in to_draw:
            tex.draw(None, rect)
        return box.bottom

    def render_extra_building_data(
        self, top, raycast: shared.RaycastHit, col_w, cs, bb, b
    ):
        content_w = col_w - b * 2
        title_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        ind_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        ind_label_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        box = pygame.Rect(god.windowing.width - col_w - bb, top + bb, col_w, bb)
        to_draw = []
        to_draw_alpha = []
        for section_name, indicators in raycast.data[-1]:
            title_tex, title_rect = god.assets.font.get_texture_and_rect(
                section_name, "white", title_h
            )
            to_draw.append((title_tex, title_rect.move_to(midtop=box.midbottom)))
            box.h += title_rect.h + bb
            for indicator in indicators:
                match indicator:
                    case ["text", color, text]:
                        text_tex, text_rect = god.assets.font.get_texture_and_rect(
                            text, color, ind_label_h, content_w
                        )
                        jump = max(ind_h, text_rect.height)
                        to_draw.append(
                            (
                                text_tex,
                                text_rect.move_to(
                                    center=(box.centerx, box.bottom + jump / 2)
                                ),
                            )
                        )
                        box.h += jump
                    case ["item", uid, count]:
                        item = ItemOD.get(uid)
                        image = god.assets.item_texs[item.name_id]
                        display_text = f"{f'(x{count}) ' if count is not None else ''}{item.display_name}"
                        text_tex, text_rect = god.assets.font.get_texture_and_rect(
                            display_text, "white", ind_label_h, content_w - ind_h / 2
                        )
                        jump = max(ind_h, text_rect.height)
                        to_draw.append(
                            (
                                image,
                                pygame.Rect(0, 0, ind_h, ind_h).move_to(
                                    midright=(box.right - b, box.bottom + jump / 2)
                                ),
                            )
                        )
                        to_draw.append(
                            (
                                text_tex,
                                text_rect.move_to(
                                    center=(
                                        box.centerx,
                                        box.bottom + jump / 2,
                                    )
                                ),
                            )
                        )
                        box.h += jump
                    case ["progress", percentage, icon_name]:
                        icon = god.assets.icons_texs[icon_name]
                        icon_size = content_w / 2
                        icon_rect = pygame.Rect(0, 0, icon_size, icon_size).move_to(
                            midtop=(box.centerx, box.bottom)
                        )
                        to_draw_alpha.append(
                            (icon, None, icon_rect, constants.UI_INTERFACE_ICON_ALPHA)
                        )
                        perc_source_h = icon.height * percentage
                        perc_icon_h = icon_rect.w * percentage
                        to_draw_alpha.append(
                            (
                                icon,
                                pygame.Rect(
                                    0,
                                    icon.height - perc_source_h,
                                    icon.height,
                                    perc_source_h,
                                ),
                                icon_rect.move_to(height=perc_icon_h).move(
                                    0, icon_rect.w - perc_icon_h
                                ),
                                constants.OPAQUE,
                            ),
                        )
                        box.h += icon_size

                box.h += bb
        box.h += bb
        render_panel_bg(box, cs)
        for tex, rect in to_draw:
            tex.draw(None, rect)
        for tex, srcrect, rect, alpha in to_draw_alpha:
            tex.alpha = alpha
            tex.draw(srcrect, rect)
        return box.bottom

    def render_drop_amount(self, top, raycast: shared.RaycastHit, col_w, cs, bb, b):
        content_w = col_w - b * 2
        text_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        text_tex, text_rect = god.assets.font.get_texture_and_rect(
            f"Drop Amount: {raycast.data}", "white", text_h
        )
        box = pygame.Rect(
            god.windowing.width - bb - col_w,
            top + bb,
            col_w,
            b * 2 + text_rect.h,
        )
        render_panel_bg(box, cs)
        text_tex.draw(None, text_rect.move_to(midtop=(box.centerx, box.top + b)))
        return box.bottom

    def render_drops(self, top, raycast: shared.RaycastHit, col_w, cs, bb, b):
        content_w = col_w - b * 2
        subtitle_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        subtitle_tex, subtitle_rect = god.assets.font.get_texture_and_rect(
            "Drops", "white", subtitle_h
        )
        drop_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        drop_name_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT

        box = pygame.Rect(
            god.windowing.width - bb - col_w,
            top + bb,
            col_w,
            bb * 3
            + subtitle_rect.h
            + bb * (len(raycast.object_data.item_drop) - 1)
            + drop_h * len(raycast.object_data.item_drop)
            + (subtitle_rect.h + bb * 3 + drop_h)
            * (raycast.object_data.break_requirements is not None),
        )
        render_panel_bg(box, cs)
        subtitle_rect = subtitle_rect.move_to(midtop=(box.centerx, box.top + bb))
        subtitle_tex.draw(None, subtitle_rect)

        for i, (item_od, amount) in enumerate(raycast.object_data.item_drop):
            amount_str = f"({amount}) " if amount > 1 else ""
            drop_tex, drop_rect = god.assets.font.get_texture_and_rect(
                f"{amount_str}{item_od.display_name}",
                "white",
                drop_name_h,
            )
            drop_rect = drop_rect.move_to(
                center=(
                    box.x + b + (content_w - drop_h) / 2,
                    subtitle_rect.bottom + bb + (drop_h + bb) * i + (drop_h / 2),
                )
            )
            drop_tex.draw(None, drop_rect)
            drop_rect = pygame.Rect(0, 0, drop_h, drop_h).move_to(
                topright=(
                    box.right - b,
                    subtitle_rect.bottom + bb + (drop_h + bb) * i,
                )
            )
            god.assets.item_texs[item_od.name_id].draw(
                None,
                drop_rect,
            )
        if raycast.object_data.break_requirements is not None:
            req_tex, req_rect = god.assets.font.get_texture_and_rect(
                "Requires (min.)", constants.UI_INFO_DESCR_COL, subtitle_h
            )
            req_rect = req_rect.move_to(midtop=(box.centerx, drop_rect.bottom + bb))
            req_tex.draw(None, req_rect)
            item_tex, item_rect = god.assets.font.get_texture_and_rect(
                raycast.object_data.break_requirements[0].display_name,
                constants.GREEN_GOOD
                if god.player.inventory_slots[constants.INVENTORY_HAND_I].contains_any(
                    raycast.object_data.break_requirements, 1
                )
                else constants.RED_BAD,
                drop_name_h,
            )
            item_tex.draw(
                None,
                item_rect.move_to(
                    center=(
                        box.x + b + (content_w - drop_h) / 2,
                        req_rect.bottom + bb + drop_h / 2,
                    )
                ),
            )
            god.assets.item_texs[
                raycast.object_data.break_requirements[0].name_id
            ].draw(
                None,
                pygame.Rect(0, 0, drop_h, drop_h).move_to(
                    topright=(box.right - b, req_rect.bottom + bb)
                ),
            )

        return box.bottom

    def render_building_interaction(
        self, top, raycast: shared.RaycastHit, col_w, cs, bb, b
    ):
        content_w = col_w - b * 2
        box = pygame.Rect(god.windowing.width - bb - col_w, top + bb, col_w, bb)
        text_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        small_text_h = content_w * constants.UI_RAYCAST_INFO_SMALL_NOTE_H_MULT
        to_draw = []
        if raycast.object_data.interface:
            if (
                god.player.pos.distance_to(raycast.hitbox.center)
                <= constants.PLAYER_INTERACT_RADIUS
            ):
                text = "- Right click to interact."
                if raycast.object_data == BuildingOD.objects.bot:
                    text += "\n- Middle click to edit the trajectory."
                if raycast.object_data.has_configuration:
                    text += "\n- CTRL+C to copy the configuration."
            else:
                text = "- Too far to interact."
                if raycast.object_data.has_configuration:
                    text += "\n- CTRL+C to copy the configuration."
            # god.assets.font.font.align = pygame.FONT_LEFT
            click_tex, click_rect = god.assets.font.get_texture_and_rect(
                text, constants.UI_INFO_DESCR_COL, small_text_h, content_w
            )
            # god.assets.font.font.align = pygame.FONT_CENTER
            to_draw.append((click_tex, click_rect.move_to(midtop=box.midbottom)))
            box.h += click_rect.h + bb
        if god.player.config_clipboard is not None:
            if god.user_input.can_paste_config():
                text = "- CTRL+V to paste configuration."
                col = "white"
            else:
                text = "- Cannot paste the configuration here."
                col = constants.YELLOW_WARNING
            paste_tex, paste_rect = god.assets.font.get_texture_and_rect(
                text, col, small_text_h, content_w
            )
            to_draw.append((paste_tex, paste_rect.move_to(midtop=box.midbottom)))
            box.h += paste_rect.h + bb
        if raycast.object_data.need_energy:
            if raycast.data[2]:
                text = "Has energy"
                col = constants.GREEN_GOOD
            else:
                text = "No energy"
                col = constants.RED_BAD
            energy_tex, energy_rect = god.assets.font.get_texture_and_rect(
                text, col, text_h
            )
            to_draw.append((energy_tex, energy_rect.move_to(midtop=box.midbottom)))
            box.h += energy_rect.h + bb
        render_panel_bg(box, cs)
        for tex, rect in to_draw:
            tex.draw(None, rect)
        return box.bottom

    def render_object_pos(self, top, raycast: shared.RaycastHit, col_w, cs, bb, b):
        too_far = god.player.pos.distance_to(raycast.hitbox.center) > (
            constants.PLAYER_REACH_RADIUS
        )
        content_w = col_w - b * 2
        split = raycast.chunk_key.split(";")
        cpos = (int(split[0]), int(split[1]))
        world_pos = shared.get_chunk_world_pos(cpos)
        text_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        text_tex, text_rect = god.assets.font.get_texture_and_rect(
            f"X: {int(world_pos.x + raycast.tile_pos[0])} Y: {-int(world_pos.y + raycast.tile_pos[1])}",
            constants.UI_INFO_DESCR_COL,
            text_h,
        )
        box = pygame.Rect(
            god.windowing.width - bb - col_w,
            top + bb,
            col_w,
            b * 2 + text_rect.h * (too_far + 1),
        )
        render_panel_bg(box, cs)
        if too_far:
            far_tex, far_rect = god.assets.font.get_texture_and_rect(
                "Too far to break", constants.RED_BAD, text_h
            )
            far_tex.draw(None, far_rect.move_to(midtop=(box.centerx, box.top + b)))
        text_tex.draw(
            None,
            text_rect.move_to(
                midtop=(
                    box.centerx,
                    box.top + b + text_rect.h * too_far,
                )
            ),
        )
        return box.bottom

    def render_main(self, bottom, raycast: shared.RaycastHit, col_w, cs, bb, b):
        content_w = col_w - b * 2
        title_h = content_w * constants.UI_RAYCAST_INFO_TITLE_H_MULT
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            raycast.object_data.display_name, "white", title_h, content_w
        )
        descr_h = title_h * constants.UI_RAYCAST_INFO_DESCR_MULT
        descr_tex, descr_rect = god.assets.font.get_texture_and_rect(
            raycast.object_data.description,
            constants.UI_INFO_DESCR_COL,
            descr_h,
            content_w,
        )

        image_w = content_w / 2
        box = pygame.Rect(
            (
                god.windowing.width - bb - col_w,
                bb + bottom,
                col_w,
                b * 4 + title_rect.h + image_w + descr_rect.h,
            )
        )
        render_panel_bg(box, cs)
        title_rect = title_rect.move_to(midtop=(box.centerx, box.top + b))
        title_tex.draw(None, title_rect)

        object_tex = None
        if raycast.type == constants.RAYCAST_TILE:
            object_tex = god.assets.tile_texs[raycast.object_data.name_id]
        elif raycast.type in [constants.RAYCAST_DROP, constants.RAYCAST_UI_ITEM]:
            object_tex = god.assets.item_texs[raycast.object_data.name_id]
        elif raycast.type == constants.RAYCAST_BUILDING:
            state = raycast.object_data.states[raycast.data[1]]
            if not state.raycast_can_use:
                state = raycast.object_data.states["default_image"]
            object_tex = god.assets.building_texs[state.image_name]
        elif raycast.type == constants.RAYCAST_VEGETATION:
            object_tex = god.assets.vegetation_texs[raycast.object_data.name_id]
        image_rect = pygame.Rect(
            box.x + b + (content_w / 2 - image_w / 2),
            title_rect.bottom + b,
            image_w,
            image_w,
        )
        if object_tex:
            object_tex.draw(None, image_rect)

        descr_tex.draw(
            None, descr_rect.move_to(midtop=(image_rect.centerx, image_rect.bottom + b))
        )

        return box.bottom
