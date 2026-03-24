import typing

import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD
from src.client.ui.panel import render_panel_bg

if typing.TYPE_CHECKING:
    from src.client.ui.ui import UIRaycastHit


class RaycastInfoUI:
    def render(self, border):
        self.b = border
        raycast = god.player.raycast
        if god.ui.inventory_open and god.ui.ui_raycast is not None:
            raycast = god.ui.ui_raycast
        if (
            raycast is None
            or raycast is constants.UI_RAYCAST_EMPTY
            or raycast.type == constants.RAYCAST_EMPTY
        ):
            return
        col_w = god.windowing.width * constants.UI_RAYCAST_INFO_W_MULT
        cs = col_w * constants.UI_RAYCAST_INFO_CORNER_SIZE_MULT
        if raycast.object_data is not None:
            bottom = self.render_main(raycast, col_w, cs, self.b, self.b * 2)
        else:
            bottom = 0
        if raycast.type == constants.RAYCAST_TILE:
            if len(raycast.object_data.item_drop) > 0:
                bottom = self.render_drops(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            bottom = self.render_tile_pos(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )
        elif raycast.type == constants.RAYCAST_UI_ITEM:
            if raycast.filter:
                bottom = self.render_slot_filter(
                    bottom, raycast, col_w, cs, self.b, self.b * 2
                )
            bottom = self.render_item_amount(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )
        elif raycast.type == constants.RAYCAST_UI_SLOT_FILTER:
            bottom = self.render_slot_filter(
                bottom, raycast, col_w, cs, self.b, self.b * 2
            )

    def render_slot_filter(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        title_h = content_w * (constants.UI_RAYCAST_INFO_MSG_H_MULT)
        text = "Unknown Filter"
        if raycast.filter[0] == constants.INVENTORY_FILTER_CATEGORY:
            text = f"Slot Whitelist: {constants.ITEM_CATEGORY_NAMES[raycast.filter[1]]}"
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            text, "white", title_h, content_w
        )
        box = pygame.Rect(
            god.windowing.width - bb - col_w, top + bb, col_w, b * 2 + title_rect.h
        )
        render_panel_bg(box, cs)
        title_tex.draw(None, title_rect.move_to(center=box.center))
        return box.bottom

    def render_drops(self, top, raycast: shared.RaycastHit, col_w, cs, bb, b):
        content_w = col_w - b * 2
        subtitle_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT
        subtitle_tex, subtitle_rect = god.assets.font.get_texture_and_rect(
            "Drops", "white", subtitle_h
        )
        drop_h = content_w * constants.UI_RAYCAST_INFO_SUBTITLE_H_MULT

        box = pygame.Rect(
            god.windowing.width - bb - col_w,
            top + bb,
            col_w,
            bb * 3
            + subtitle_rect.h
            + bb * (len(raycast.object_data.item_drop) - 1)
            + drop_h * len(raycast.object_data.item_drop)
            + (subtitle_rect.h + bb * 3 + drop_h)
            * (raycast.object_data.break_requirements_id is not None),
        )
        render_panel_bg(box, cs)
        subtitle_rect = subtitle_rect.move_to(midtop=(box.centerx, box.top + bb))
        subtitle_tex.draw(None, subtitle_rect)

        for i, (item_od, amount) in enumerate(raycast.object_data.item_drop):
            drop_name_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
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
        if raycast.object_data.break_requirements_id is not None:
            req_tex, req_rect = god.assets.font.get_texture_and_rect(
                "Requires", constants.UI_RAYCAST_INFO_DESCR_COL, subtitle_h
            )
            req_rect = req_rect.move_to(midtop=(box.centerx, drop_rect.bottom + bb))
            req_tex.draw(None, req_rect)
            item = ItemOD.get(raycast.object_data.break_requirements_id)
            item_tex, item_rect = god.assets.font.get_texture_and_rect(
                item.display_name,
                constants.GREEN_GOOD
                if god.player.inventory_slots[constants.INVENTORY_HAND_I].contains(
                    item, 1
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
            god.assets.item_texs[item.name_id].draw(
                None,
                pygame.Rect(0, 0, drop_h, drop_h).move_to(
                    topright=(box.right - b, req_rect.bottom + bb)
                ),
            )

        return box.bottom

    def render_item_amount(self, top, raycast: "UIRaycastHit", col_w, cs, bb, b):
        content_w = col_w - b * 2
        text_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        text_tex, text_rect = god.assets.font.get_texture_and_rect(
            f"Inventory: {god.player.count_item(raycast.item)}", "white", text_h
        )
        text2_tex, text2_rect = god.assets.font.get_texture_and_rect(
            f"Slot: {raycast.amount}/{raycast.item.stack_size}",
            constants.UI_RAYCAST_INFO_DESCR_COL,
            text_h,
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

    def render_tile_pos(self, top, raycast: shared.RaycastHit, col_w, cs, bb, b):
        too_far = (
            god.player.pos.distance_to(raycast.hitbox.center)
            > constants.PLAYER_REACH_RADIUS
        )
        content_w = col_w - b * 2
        split = raycast.chunk_key.split(";")
        cpos = (int(split[0]), int(split[1]))
        text_h = content_w * constants.UI_RAYCAST_INFO_MSG_H_MULT
        text_tex, text_rect = god.assets.font.get_texture_and_rect(
            f"X: {cpos[0] * constants.CHUNK_SIZE + raycast.tile_pos[0]} Y: {cpos[1] * constants.CHUNK_SIZE + raycast.tile_pos[1]}",
            constants.UI_RAYCAST_INFO_DESCR_COL,
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
                "Too far", constants.RED_BAD, text_h
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

    def render_main(self, raycast: shared.RaycastHit, col_w, cs, bb, b):
        content_w = col_w - b * 2
        title_h = content_w * constants.UI_RAYCAST_INFO_TITLE_H_MULT
        title_tex, title_rect = god.assets.font.get_texture_and_rect(
            raycast.object_data.display_name, "white", title_h, content_w
        )
        descr_h = title_h * constants.UI_RAYCAST_INFO_DESCR_MULT
        descr_tex, descr_rect = god.assets.font.get_texture_and_rect(
            raycast.object_data.description,
            constants.UI_RAYCAST_INFO_DESCR_COL,
            descr_h,
            content_w,
        )

        image_w = content_w / 2
        box = pygame.Rect(
            (
                god.windowing.width - bb - col_w,
                bb,
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
        elif raycast.type == constants.RAYCAST_UI_ITEM:
            object_tex = god.assets.item_texs[raycast.object_data.name_id]
        image_rect = pygame.Rect(
            box.x + b + (content_w / 2 - image_w / 2),
            title_rect.bottom + b,
            image_w,
            image_w,
        )
        object_tex.draw(None, image_rect)

        descr_tex.draw(
            None, descr_rect.move_to(midtop=(image_rect.centerx, image_rect.bottom + b))
        )

        return box.bottom
