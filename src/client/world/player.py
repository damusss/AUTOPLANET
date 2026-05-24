import pygame

from src import shared
from src import constants
from src.client import god
from src.object_data import ItemOD, BuildingOD
from src.client.world.chunk import LightData

if constants.NEW_RENDER:
    from pygame._render import Texture
else:
    from pygame._sdl2 import Texture


class PlayerLike:
    pos: pygame.Vector2
    vel: pygame.Vector2
    texture: Texture
    light: LightData
    name_texture: Texture

    def get_name_texture(self, name): ...


class OtherPlayer(PlayerLike):
    def __init__(self, pos, player_id, name):
        self.id = player_id
        self.name = name
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.frame_kind = "idle"
        self.frame_index = 0
        self.texture = None
        self.building_preview: list = None
        self.break_data: tuple[int, tuple[float, float], float] | None = None
        self.light = LightData(
            f"other_player_{player_id}",
            constants.PLAYER_LIGHT_RADIUS,
            constants.PLAYER_LIGHT_INTENSITY,
            constants.PLAYER_LIGHT_COLOR,
        )

    def frame(self):
        self.pos += self.vel * god.dt
        frames = (
            god.assets.player_idle_texs
            if self.frame_kind == "idle"
            else god.assets.player_run_texs
        )
        self.texture = frames[int(self.frame_index) % len(frames)]


class Player(PlayerLike):
    def __init__(self):
        god.player = self
        self.pos = pygame.Vector2(0, constants.PLAYER_SPAWN_Y)
        self.vel = pygame.Vector2()
        self.frame_index = 0
        self.frame_speed = constants.IDLE_FRAME_SPEED
        self.frames = god.assets.player_idle_texs
        self.texture: Texture = self.frames[0]
        self.last_frame = pygame.time.get_ticks()
        self.running = False
        self.jumping = False
        self.energy = constants.PLAYER_MAX_ENERGY
        self.health = constants.PLAYER_MAX_HEALTH
        self.raycast: shared.RaycastHit = None
        self.edit_trajectory_bot = None
        self.edit_trajectory_kind = "input"
        self.break_start_time = None
        self.break_mult = 1
        self.building_preview: BuildingOD | None = None
        self.building_available = constants.BUILDING_STATUS_OBSTRUCTED
        self.craft_queue: list[shared.CraftQueueItem] = []
        self.inventory_slots = [
            shared.Slot(None, 0, None, i, "player")
            for i in range(constants.INVENTORY_COLS * constants.INVENTORY_ROWS + 1)
        ]
        for slot in self.inventory_slots:
            slot.hitbox = pygame.Rect()
        self.light = LightData(
            "player",
            constants.PLAYER_LIGHT_RADIUS,
            constants.PLAYER_LIGHT_INTENSITY,
            constants.PLAYER_LIGHT_COLOR,
        )

    @property
    def hitbox(self):
        return pygame.FRect(
            pygame.Vector2(
                self.pos.x - constants.PLAYER_HITBOX[0] / 2,
                self.pos.y - constants.PLAYER_HITBOX[1] / 2,
            )
            + constants.PLAYER_HITBOX_OFFSET,
            constants.PLAYER_HITBOX,
        )

    def set_building_preview(self, preview):
        if preview is None:
            self.building_preview = None
            if not god.input.manual_energy_debug:
                god.rendering.energy_debug = False
        else:
            self.building_preview = preview
            self.building_available = constants.BUILDING_STATUS_OBSTRUCTED
            if (
                self.building_preview.need_energy
                or self.building_preview.energy_endpoint_type
                != constants.ENDPOINT_MACHINE
            ):
                god.rendering.energy_debug = True
                god.input.manual_energy_debug = False

    def set_edit_trajectory(self, bid):
        if bid is None:
            self.edit_trajectory_bot = None
            self.edit_trajectory_kind = "input"
        else:
            self.edit_trajectory_bot = bid

    def edit_trajectory_validate_hover(self):
        if (
            self.raycast is not None
            and self.building_preview is None
            and self.raycast.type == constants.RAYCAST_BUILDING
            and self.raycast.data[0] != self.edit_trajectory_bot
        ):
            available = constants.BUILDING_STATUS_OBSTRUCTED
            if self.raycast.object_data.static and (
                (
                    self.raycast.object_data.inventory_kind
                    == constants.INVENTORY_KIND_IN_OUT
                )
                or (
                    self.edit_trajectory_kind == constants.INVENTORY_KIND_INPUT
                    and self.raycast.object_data.inventory_kind
                    == constants.INVENTORY_KIND_OUTPUT
                )
                or (
                    self.edit_trajectory_kind == constants.INVENTORY_KIND_OUTPUT
                    and self.raycast.object_data.inventory_kind
                    == constants.INVENTORY_KIND_INPUT
                )
            ):
                available = constants.BUILDING_STATUS_AVAILABLE
            return available
        return None

    def count_item(self, item):
        count = 0
        for slot in self.inventory_slots:
            if not slot.empty and slot.item == item:
                count += slot.amount
        return count

    def update_inventory(self, data):
        for i, (uid, amount, filter_) in enumerate(data):
            prev_amount = self.inventory_slots[i].amount
            self.inventory_slots[i].item = ItemOD.get(uid) if uid is not None else None
            self.inventory_slots[i].amount = amount
            self.inventory_slots[i].filter = filter_
            if (
                prev_amount != amount
                and self.inventory_slots[i]
                is god.ui.inventory.floating_slot.source_slot
            ):
                god.ui.inventory.floating_slot.amount += amount - prev_amount
                if god.ui.inventory.floating_slot.amount <= 0:
                    god.ui.inventory.floating_slot.source_slot = None

    def frame(self):
        self.pos += self.vel * god.dt

        cur_frame = self.frame_index
        self.jumping = abs(self.vel.y) > constants.ZERO

        if not self.jumping:
            if self.running and self.frames != god.assets.player_run_texs:
                self.frames = god.assets.player_run_texs
                self.frame_speed = constants.RUN_FRAME_SPEED
                self.frame_index = self.frame_index % len(self.frames)
            elif self.frames != god.assets.player_idle_texs:
                self.frames = god.assets.player_idle_texs
                self.frame_speed = constants.IDLE_FRAME_SPEED
                self.frame_index = self.frame_index % len(self.frames)

            if pygame.time.get_ticks() - self.last_frame >= self.frame_speed * 1000:
                self.last_frame = pygame.time.get_ticks()
                self.frame_index += 1
                if self.frame_index >= len(self.frames):
                    self.frame_index = 0
                self.texture = self.frames[self.frame_index]
        else:
            if not self.running:
                self.texture = god.assets.player_idle_texs[-1]
            else:
                self.texture = god.assets.player_run_texs[0]

        if cur_frame != self.frame_index:
            god.client.conn.mail(
                constants.MAIL_ANIMATION_UPDATE,
                frame_kind="run" if self.running else "idle",
                frame_index=self.frame_index,
            )
        if self.building_preview is not None:
            god.client.conn.mail(
                constants.MAIL_BUILDING_AVAILABLE,
                building_uid=self.building_preview.uid,
                pos=tuple(god.input.mouse_world),
            )
            if self.count_item(self.building_preview.item) < 1:
                self.set_building_preview(None)
        if self.edit_trajectory_bot is not None:
            if self.edit_trajectory_bot not in god.world.moving_buildings_data:
                self.set_edit_trajectory(None)
