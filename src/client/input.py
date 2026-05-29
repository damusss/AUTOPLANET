import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import BuildingOD


class Input:
    def __init__(self):
        god.user_input = self
        self.input_dir = pygame.Vector2()
        self.mouse_screen = pygame.Vector2()
        self.mouse_world = pygame.Vector2()
        self.manual_energy_debug = False
        self.place_time = 0
        self.place_pos = None
        self.drag_enabled = False
        # temp connect to server
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0))

    def event(self, event: pygame.Event):
        if event.type == pygame.MOUSEWHEEL:
            god.world.camera.zoom_event(event.y)
        if event.type == pygame.MOUSEBUTTONUP:
            self.drag_enabled = False
            if event.button == pygame.BUTTON_RIGHT:
                god.ui.inventory.end_right_pan()
            elif event.button == pygame.BUTTON_LEFT:
                god.ui.inventory.end_left_pan()
            god.client.conn.mail(
                constants.MAIL_INPUT_EVENT, input_type=event.type, button=event.button
            )
        if event.type == pygame.MOUSEBUTTONDOWN:
            if god.ui.inventory_open:
                god.ui.mouse_clicked(event)
            if god.ui.can_interact_world():
                if (
                    god.player.building_preview is not None
                    and event.button == pygame.BUTTON_LEFT
                ):
                    god.client.conn.mail(
                        constants.MAIL_PLACE_BUILDING,
                        building_uid=god.player.building_preview.uid,
                        pos=tuple(self.mouse_world),
                    )
                    self.place_time = god.world.get_ticks()
                    self.place_pos = self.mouse_world
                elif (
                    event.button == pygame.BUTTON_RIGHT
                    and god.player.raycast is not None
                    and god.player.raycast.type == constants.RAYCAST_BUILDING
                ):
                    if god.player.edit_trajectory_bot is None:
                        god.client.conn.mail(
                            constants.MAIL_BUILDING_INTERACT,
                            building_id=god.player.raycast.data[0],
                            unsubscribe=False,
                        )
                    else:
                        available = god.player.edit_trajectory_validate_hover()
                        if available == constants.BUILDING_STATUS_AVAILABLE:
                            god.client.conn.mail(
                                constants.MAIL_BOT_TRAJECTORY,
                                bot_id=god.player.edit_trajectory_bot,
                                kind=god.player.edit_trajectory_kind,
                                target_id=god.player.raycast.data[0],
                            )
                            god.player.edit_trajectory_kind = shared.other_kind(
                                god.player.edit_trajectory_kind
                            )
                        elif (
                            god.player.raycast.data[0] == god.player.edit_trajectory_bot
                        ):
                            for kind in [
                                constants.INVENTORY_KIND_INPUT,
                                constants.INVENTORY_KIND_OUTPUT,
                            ]:
                                god.client.conn.mail(
                                    constants.MAIL_BOT_TRAJECTORY,
                                    bot_id=god.player.edit_trajectory_bot,
                                    kind=kind,
                                    target_id=None,
                                )

                elif (
                    event.button == pygame.BUTTON_MIDDLE
                    and not god.ui.inventory_open
                    and god.player.raycast is not None
                    and god.player.raycast.type == constants.RAYCAST_BUILDING
                    and god.player.raycast.object_data == BuildingOD.objects.bot
                ):
                    if god.player.edit_trajectory_bot == god.player.raycast.data[0]:
                        god.player.set_edit_trajectory(None)
                        if (
                            god.player.count_item(god.player.raycast.object_data.item)
                            >= 1
                        ):
                            god.player.set_building_preview(
                                god.player.raycast.object_data
                            )
                    else:
                        god.player.set_edit_trajectory(god.player.raycast.data[0])
                elif (
                    event.button == pygame.BUTTON_MIDDLE
                    and not god.ui.inventory_open
                    and god.player.raycast is not None
                    and god.player.raycast.type == constants.RAYCAST_BUILDING
                    and god.player.raycast.object_data != BuildingOD.objects.bot
                ):
                    if god.player.count_item(god.player.raycast.object_data.item) >= 1:
                        god.player.set_building_preview(god.player.raycast.object_data)
                elif (
                    event.button == pygame.BUTTON_MIDDLE
                    and not god.ui.inventory_open
                    and god.player.edit_trajectory_bot is not None
                ):
                    if (
                        god.player.edit_trajectory_kind
                        == constants.INVENTORY_KIND_INPUT
                    ):
                        god.player.edit_trajectory_kind = (
                            constants.INVENTORY_KIND_OUTPUT
                        )
                    else:
                        god.player.edit_trajectory_kind = constants.INVENTORY_KIND_INPUT
                else:
                    god.client.conn.mail(
                        constants.MAIL_INPUT_EVENT,
                        input_type=event.type,
                        button=event.button,
                    )
        # if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
        #    god.client.conn.mail(constants.MAIL_INPUT_EVENT, input_type=event.type, button=None)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSLASH:
                god.rendering.debug = not god.rendering.debug
            if event.key == pygame.K_F1:
                god.rendering.energy_debug = not god.rendering.energy_debug
                self.manual_energy_debug = True
            if event.key == pygame.K_F2:
                god.rendering.trajectory_debug = not god.rendering.trajectory_debug
            if event.key == pygame.K_TAB:
                god.client.conn.mail(constants.MAIL_TOGGLE_PAUSE)
            if event.mod & pygame.KMOD_CTRL:
                if event.key == pygame.K_c:
                    god.client.conn.mail(constants.MAIL_COPY_CONFIG, reset=False)
                elif event.key == pygame.K_v:
                    if self.can_paste_config():
                        god.client.conn.mail(constants.MAIL_PASTE_CONFIG)
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_e:
                god.ui.toggle_inventory(True)
            if event.key == pygame.K_ESCAPE:
                if god.ui.inventory_open and god.ui.overlay_menu_func is not None:
                    god.ui.overlay_menu_func = None
                else:
                    god.player.set_building_preview(None)
                    god.player.set_edit_trajectory(None)
                    god.rendering.energy_debug = False
                    god.rendering.trajectory_debug = False
                    if god.ui.inventory_open:
                        god.ui.toggle_inventory()
            if event.key == pygame.K_q:
                god.player.set_building_preview(None)
                god.player.set_edit_trajectory(None)
                if god.ui.inventory_open:
                    god.ui.inventory.floating_slot.source_slot = None
                god.client.conn.mail(constants.MAIL_COPY_CONFIG, reset=True)

    def can_paste_config(self):
        return (
            god.player.raycast is not None
            and god.player.config_clipboard is not None
            and god.player.raycast.type == constants.RAYCAST_BUILDING
            and god.player.raycast.object_data.has_configuration
            and god.player.raycast.object_data
            == god.player.config_clipboard.building_od
        )

    def frame(self):
        self.mouse_screen = pygame.Vector2(pygame.mouse.get_pos())
        mouse_world = pygame.Vector2(self.mouse_world)
        self.mouse_world = god.camera.from_screen(self.mouse_screen)
        input_dir = pygame.Vector2()
        pressed = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            input_dir.x = -1
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            input_dir.x = 1
        if pressed[pygame.K_SPACE] or pressed[pygame.K_w] or pressed[pygame.K_UP]:
            input_dir.y = -1
        if god.ui.inventory_open:
            if god.ui.inventory.right_panning:
                god.ui.inventory.right_pan()
            if god.ui.inventory.left_panning:
                god.ui.inventory.left_pan()
        if input_dir != self.input_dir:
            self.input_dir = input_dir
            god.player.running = abs(self.input_dir.x) > 1e-3
            god.client.conn.mail(constants.MAIL_INPUT_DIR, dir=tuple(input_dir))
        if mouse_world != self.mouse_world:
            god.client.conn.mail(constants.MAIL_MOUSE_POS, pos=tuple(self.mouse_world))
        if (
            mouse_pressed[0]
            and self.place_pos is not None
            and god.player.building_preview is not None
            and pygame.time.get_ticks() - self.place_time
            >= constants.DRAG_PLACE_START_COOLDOWN
        ):
            self.drag_enabled = True
            if self.mouse_world.distance_squared_to(self.place_pos) > 0.5 * 0.5:
                self.place_pos = self.mouse_world
                god.client.conn.mail(
                    constants.MAIL_PLACE_BUILDING,
                    building_uid=god.player.building_preview.uid,
                    pos=tuple(self.mouse_world),
                )
