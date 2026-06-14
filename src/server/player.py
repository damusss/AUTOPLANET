import typing
from collections import deque

import pygame

from src import shared
from src import constants
from src.server import god
from src.server import terrain
from src.object_data import ItemOD, TileOD
from src.server.drop import Drop
from src.server.inventory import Inventory

if typing.TYPE_CHECKING:
    from src.server.server import ClientInterface
    from src.server.building import StaticBuilding, MovingBuilding


class Player:
    def __init__(self, client):
        self.client: ClientInterface = client
        self.vel = pygame.Vector2()
        self.pos = pygame.Vector2(0, terrain.get_surface_height(0) - 1)
        self.input_dir = pygame.Vector2()
        self.health = constants.PLAYER_MAX_HEALTH
        self.energy = constants.PLAYER_MAX_ENERGY
        self.raycast: shared.RaycastHit | None = None
        self.inventory = Inventory(self)
        self.hotbar: list[int | None] = [None] * constants.INVENTORY_HOTBAR_SIZE
        # temp
        self.hotbar[0] = ItemOD.objects.energy_plant.uid
        self.hotbar[1] = ItemOD.objects.computer.uid
        self.hotbar[2] = ItemOD.objects.copper_platform.uid
        # endtemp
        self.craft_queue: deque[shared.CraftQueueItem] = deque()
        self.config_clipboard: shared.ConfigClipboard | None = None
        self.break_start_time = None
        self.break_data: shared.RaycastHit | None = None
        self.break_count: int = 0
        self.last_mold_damage = 0
        self.last_regen = 0
        self.fall_vel = 0
        self.pos_when_terminal_vel = None

        self.stats_dirty = True
        self.client_frame_kind = "idle"
        self.client_frame_index = 0
        self.client_loaded_chunks = set()
        self.client_input_dir = pygame.Vector2()
        self.client_chunks_queue = deque()
        self.client_mouse_pos = pygame.Vector2()
        self.client_mouse_pressing = False
        self.client_building_preview = None
        self.client_building_preview_clear_after = 1
        self.client_subscribed_building: "StaticBuilding|MovingBuilding|None" = None

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

    @property
    def break_mult(self):
        return constants.REITERATE_BREAK_TIME_MULT if (self.break_count > 0) else 1

    @property
    def raycast_flag(self):
        if self.client_building_preview is not None:
            return constants.RAYCASTFLAG_INFO
        hand_slot = self.inventory.slots[constants.INVENTORY_HAND_I]
        if not hand_slot.empty and hand_slot.item == ItemOD.objects.mold_spray:
            return constants.RAYCASTFLAG_ALL_INFO
        return constants.RAYCASTFLAG_INFO

    def damage(self, damage):
        self.health = pygame.math.clamp(
            self.health - damage,
            0,
            constants.PLAYER_MAX_HEALTH,
        )
        self.stats_dirty = True
        self.last_regen = god.world.get_ticks()

    def add_to_craft_queue(self, item, amount, phantom):
        for craft_item in self.craft_queue:
            if craft_item.item == item and craft_item.phantom == phantom:
                craft_item.amount += amount
                return
        self.craft_queue.append(shared.CraftQueueItem(item, amount, phantom))

    def try_craft_item(self, item_uid):
        item = ItemOD.get(item_uid)
        status = shared.craft_availability_status(item, self.inventory.count)
        if status.availability not in [
            constants.CRAFT_READY,
            constants.CRAFT_READY_SUBSTEP,
        ]:
            return
        for item_uid, amount in status.counted_items.items():
            self.inventory.remove(ItemOD.get(item_uid), amount)
        for item_od, amount in status.intermediate_queue:
            self.add_to_craft_queue(item_od, amount, True)
        self.add_to_craft_queue(item, 1, False)

    def client_hotbar_action(self, i, item_uid):
        if i >= len(self.hotbar) or (
            item_uid is not None and self.inventory.count(ItemOD.get(item_uid)) < 1
        ):
            return
        self.hotbar[i] = item_uid
        self.stats_dirty = True

    def frame(self, rects, drops_data, moving_data):
        self.input_dir.x = pygame.math.lerp(
            self.input_dir.x, self.client_input_dir.x, god.dt * 10, True
        )
        jump_mult = 1
        prev_dir = self.input_dir.y
        self.input_dir.y = self.client_input_dir.y
        if abs(self.vel.y) < constants.ZERO:
            if abs(self.input_dir.y) < constants.ZERO:
                self.energy += constants.PLAYER_ENERGY_REGEN_SPEED * god.dt
            if (
                prev_dir != self.input_dir.y
                and abs(prev_dir) < constants.ZERO
                and (
                    (
                        ground := god.world.raycast(
                            (self.pos.x, self.pos.y + 0.8),
                            constants.RAYCASTFLAG_COLLIDER,
                        )
                    )
                    is not None
                    and ground.hitbox is not None
                )
            ):
                jump_mult = 12

        self.vel.x = self.input_dir.x * constants.PLAYER_SPEED
        self.vel.y += constants.GRAVITY * god.dt

        if self.energy < constants.ZERO:
            jump_mult = 0
        if abs(self.input_dir.y) > constants.ZERO:
            increase = (
                jump_mult * self.input_dir.y * constants.PLAYER_JUMP_SPEED * god.dt
            )
            self.vel.y += increase
            self.energy -= constants.PLAYER_ENERGY_DEPLEAT_SPEED * god.dt

        self.energy = pygame.math.clamp(self.energy, 0, constants.PLAYER_MAX_ENERGY)
        self.vel.y = pygame.math.clamp(
            self.vel.y, constants.PLAYER_MAX_VEL, constants.PLAYER_TERMINAL_VEL
        )

        self.pos.x += self.vel.x * god.dt
        self.collisions_x(rects)
        self.pos.y += self.vel.y * god.dt
        self.collisions_y(rects)

        if abs(self.vel.y) > constants.ZERO:
            self.fall_vel = self.vel.y
            if abs(constants.PLAYER_TERMINAL_VEL - self.fall_vel) < constants.ZERO:
                if self.pos_when_terminal_vel is None:
                    self.pos_when_terminal_vel = self.pos.y
            else:
                self.pos_when_terminal_vel = None
        elif (
            ground := god.world.raycast(
                (self.pos.x, self.pos.y + 0.8),
                constants.RAYCASTFLAG_COLLIDER,
            )
        ) is not None and ground.hitbox is not None:
            if self.fall_vel > constants.SAFE_FALL_VEL:
                fell_tiles = 0
                if self.pos_when_terminal_vel is not None:
                    fell_tiles = round(self.pos.y - self.pos_when_terminal_vel)
                self.damage(
                    fell_tiles * constants.FALL_DAMAGE_PER_TILE
                    + constants.FALL_DAMAGE
                    * (
                        (self.fall_vel - constants.SAFE_FALL_VEL)
                        / (constants.PLAYER_TERMINAL_VEL - constants.SAFE_FALL_VEL)
                    )
                )
            self.pos_when_terminal_vel = None
            self.fall_vel = 0

        if self.client_building_preview is not None:
            if self.client_building_preview_clear_after <= 0:
                self.client_building_preview = None
            self.client_building_preview_clear_after -= 1

        if self.health < constants.PLAYER_MAX_HEALTH:
            if (
                god.world.get_ticks() - self.last_regen
                >= constants.PLAYER_HEALTH_REGEN_COOLDOWN
            ):
                self.damage(-constants.PLAYER_HEALTH_REGEN_AMOUNT)

        self.handle_mouse_input()
        self.handle_craft_queue()

        self.mail_physics(drops_data, moving_data)
        if self.inventory.dirty or self.stats_dirty:
            self.mail_stats()

    def drops_collisions(self, drops: list[Drop], update: bool, drops_data: list):
        hitbox = self.hitbox
        for drop in list(drops):
            if drop.hitbox.colliderect(hitbox):
                not_added = self.inventory.add(drop.item, drop.amount)
                if not_added == 0:
                    drop.destroy()
                else:
                    drop.amount = not_added
            if update:
                drop.frame()
            drops_data.append(drop.get_client_data())

    def handle_craft_queue(self):
        if len(self.craft_queue) <= 0:
            return
        craft_item = self.craft_queue[0]
        if craft_item.start_time is None:
            craft_item.start_time = god.world.get_ticks()
        if (
            god.world.get_ticks() - craft_item.start_time
            >= craft_item.item.create_data.time_s * 1000
        ):
            if not craft_item.phantom:
                left = self.inventory.add(craft_item.item, 1)
                if left > 0:
                    god.world.drop(self.pos, craft_item.item, 1)
            craft_item.amount -= 1
            craft_item.start_time = god.world.get_ticks()
            if craft_item.amount <= 0:
                self.craft_queue.popleft()

    def handle_mouse_input(self):
        if not self.client_mouse_pressing:
            self.break_count = 0
        if self.break_data is not None:
            if (
                self.raycast is None
                or self.raycast.type == constants.RAYCAST_EMPTY
                or not self.client_mouse_pressing
                or self.break_data.hitbox != self.raycast.hitbox
            ):
                self.break_data = None
                self.client.conn.mail(constants.MAIL_BREAK_START, time=None, mult=None)
            else:
                if (
                    god.world.get_ticks() - self.break_start_time
                    >= self.break_data.object_data.break_time_s * 1000 * self.break_mult
                ):
                    hand_slot = self.inventory.slots[constants.INVENTORY_HAND_I]
                    if (
                        not hand_slot.empty
                        and hand_slot.item == ItemOD.objects.mold_spray
                    ):
                        if self.inventory.has(
                            ItemOD.objects.ammonia, constants.MOLD_SPRAY_CONSUME_AMOUNT
                        ):
                            if god.world.mold.purge_infection(self.raycast):
                                self.inventory.remove(
                                    ItemOD.objects.ammonia,
                                    constants.MOLD_SPRAY_CONSUME_AMOUNT,
                                )
                    else:
                        god.world.break_raycast(
                            self.break_data,
                            hand_slot.item,
                        )
                        self.break_count += 1
                    self.client.conn.mail(
                        constants.MAIL_BREAK_START, time=None, mult=None
                    )
        else:
            if (
                self.client_mouse_pressing
                and self.raycast is not None
                and self.raycast.type != constants.RAYCAST_EMPTY
            ):
                close_enough = (
                    self.pos.distance_to(self.raycast.hitbox.center)
                    <= constants.PLAYER_REACH_RADIUS
                )
                if (
                    close_enough
                    and hasattr(self.raycast.object_data, "break_requirements")
                    and (
                        self.raycast.object_data.break_requirements is None
                        or self.inventory.slots[
                            constants.INVENTORY_HAND_I
                        ].contains_any(self.raycast.object_data.break_requirements, 1)
                    )
                    and self.raycast.object_data.break_time_s > 0
                ):
                    self.break_data = self.raycast
                    self.break_start_time = god.world.get_ticks()
                    self.client.conn.mail(
                        constants.MAIL_BREAK_START, time="now", mult=self.break_mult
                    )
                else:
                    if (
                        close_enough
                        and self.raycast.object_data == TileOD.objects.mold_patch
                    ):
                        if (
                            god.world.get_ticks() - self.last_mold_damage
                            >= constants.MOLD_BREAK_DAMAGE_COOLDOWN
                        ):
                            self.damage(constants.MOLD_BREAK_DAMAGE)
                            self.last_mold_damage = god.world.get_ticks()

    def collisions_x(self, rects: list[pygame.FRect]):
        prev_hitbox = self.hitbox
        hitbox = self.hitbox
        for rect in rects:
            if rect.colliderect(hitbox):
                if (
                    hitbox.bottom <= rect.top + constants.ZERO * 100
                    or hitbox.top >= rect.bottom - constants.ZERO * 100
                ):
                    continue
                do_break = False
                if rect.centerx > hitbox.right > rect.left:
                    hitbox.right = rect.left - constants.ZERO
                    self.vel.x = constants.ZERO
                    self.input_dir.x = 0
                    do_break = True
                elif rect.centerx < hitbox.left < rect.right:
                    hitbox.left = rect.right + constants.ZERO
                    self.vel.x = -constants.ZERO
                    self.input_dir.x = -constants.ZERO
                    do_break = True
                if do_break:
                    self.pos.x += hitbox.x - prev_hitbox.x
                    break

    def collisions_y(self, rects: list[pygame.FRect]):
        prev_hitbox = self.hitbox
        hitbox = self.hitbox
        for rect in rects:
            if rect.colliderect(hitbox):
                do_break = False
                if rect.centery > hitbox.bottom > rect.top:
                    hitbox.bottom = rect.top
                    self.vel.y = 0
                    self.input_dir.y = 0
                    do_break = True
                elif rect.centery < hitbox.top < rect.bottom:
                    hitbox.top = rect.bottom
                    self.vel.y = 0
                    do_break = True
                if do_break:
                    self.pos.y += hitbox.y - prev_hitbox.y
                    break

    def mail_physics(self, drops_data, moving_data):
        other_player_stats = {}
        for player in god.server.world.players.values():
            if player is self:
                continue
            other_player_stats[player.client.id] = {
                "p": [round(p, constants.DIGIT_PRECISION) for p in tuple(player.pos)],
                "v": [round(p, constants.DIGIT_PRECISION) for p in tuple(player.vel)],
                "fk": player.client_frame_kind,
                "fi": player.client_frame_index,
                "bp": player.client_building_preview,
                "ba": [
                    shared.eval_delta(player.break_start_time),
                    player.break_data.hitbox.center,
                    player.break_data.object_data.break_time_s * player.break_mult,
                    [player.break_data.object_data.uid, player.break_data.data[0]]
                    if player.break_data.type == constants.RAYCAST_BUILDING
                    else None,
                ]
                if player.break_data is not None
                else None,
            }

        self.client.conn.mail(
            constants.MAIL_PLAYER_PHYSICS,
            p=tuple(self.pos),
            v=tuple(self.vel),
            e=self.energy,
            r=self.raycast.get_client_data()
            if self.raycast and self.raycast.type != constants.RAYCAST_EMPTY
            else None,
            op=other_player_stats,
            ds=drops_data,
            ms=moving_data,
            cq=[item.get_client_data() for item in self.craft_queue],
        )

    def mail_stats(self):
        self.client.conn.mail(
            constants.MAIL_PLAYER_STATS,
            health=self.health,
            inventory=self.inventory.get_client_data(),
            hotbar=self.hotbar,
        )
        self.inventory.dirty = False
        self.stats_dirty = False
