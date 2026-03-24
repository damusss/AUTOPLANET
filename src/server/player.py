import typing
from collections import deque

import pygame

from src import shared
from src import mailbox
from src import constants
from src.server import god
from src.server import terrain
from src.object_data import ItemOD
from src.server.inventory import Inventory

if typing.TYPE_CHECKING:
    from src.server.server import ClientInterface


class Player:
    def __init__(self, client):
        self.client: ClientInterface = client
        self.vel = pygame.Vector2()
        self.pos = pygame.Vector2(0, terrain.get_surface_height(0) - 1)
        self.input_dir = pygame.Vector2()
        self.health = constants.PLAYER_MAX_HEALTH
        self.energy = constants.PLAYER_MAX_ENERGY
        self.raycast: shared.RaycastHit = None
        self.inventory = Inventory()

        self.break_start_time = None
        self.break_data: shared.RaycastHit = None

        self.client_frame_kind = "idle"
        self.client_frame_index = 0
        self.client_loaded_chunks = set()
        self.client_input_dir = pygame.Vector2()
        self.client_chunks_queue = deque()
        self.client_mouse_pos = pygame.Vector2()
        self.client_mouse_pressing = False

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

    def frame(self, rects, drops_data):
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
                    (ground := god.world.raycast((self.pos.x, self.pos.y + 0.8)))
                    is not None
                    and ground.type == constants.RAYCAST_TILE
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

        self.handle_mouse_input()
        self.mail_physics(drops_data)
        if self.inventory.dirty:
            self.mail_stats()

    def mail_physics(self, drops_data):
        other_player_stats = {}
        for player in god.server.world.players.values():
            if player is self:
                continue
            other_player_stats[player.client.id] = {
                "pos": (round(p, constants.DIGIT_PRECISION) for p in tuple(player.pos)),
                "vel": (round(p, constants.DIGIT_PRECISION) for p in tuple(player.vel)),
                "frame_kind": player.client_frame_kind,
                "frame_index": player.client_frame_index,
            }

        self.client.conn.mail(
            mailbox.MAIL_PLAYER_PHYSICS,
            pos=tuple(self.pos),
            vel=tuple(self.vel),
            energy=self.energy,
            raycast=self.raycast.get_client_data()
            if self.raycast and self.raycast.type != constants.RAYCAST_EMPTY
            else None,
            other_players=other_player_stats,
            drops=drops_data,
        )

    def mail_stats(self):
        self.client.conn.mail(
            mailbox.MAIL_PLAYER_STATS,
            health=self.health,
            inventory=self.inventory.get_client_data(),
        )
        self.inventory.dirty = False

    def handle_mouse_input(self):
        if self.break_data is not None:
            if (
                self.raycast is None
                or self.raycast.type == constants.RAYCAST_EMPTY
                or not self.client_mouse_pressing
                or self.break_data.hitbox != self.raycast.hitbox
            ):
                self.break_data = None
                self.client.conn.mail(mailbox.MAIL_BREAK_START, time=None)
            else:
                if (
                    pygame.time.get_ticks() - self.break_start_time
                    >= self.break_data.object_data.break_time_s * 1000
                ):
                    god.world.break_raycast(self.break_data)
                    self.client.conn.mail(mailbox.MAIL_BREAK_START, time=None)
        else:
            if (
                self.client_mouse_pressing
                and self.raycast is not None
                and self.raycast.type != constants.RAYCAST_EMPTY
            ):
                if self.pos.distance_to(
                    self.raycast.hitbox.center
                ) <= constants.PLAYER_REACH_RADIUS and (
                    self.raycast.object_data.break_requirements_id is None
                    or self.inventory.slots[constants.INVENTORY_HAND_I].contains(
                        ItemOD.get(self.raycast.object_data.break_requirements_id), 1
                    )
                ):
                    self.break_data = self.raycast
                    self.break_start_time = pygame.time.get_ticks()
                    self.client.conn.mail(mailbox.MAIL_BREAK_START, time="now")

    def collisions_x(self, rects: list[pygame.FRect]):
        prev_hitbox = self.hitbox
        hitbox = self.hitbox
        for rect in rects:
            if rect.colliderect(hitbox):
                do_break = False
                if hitbox.right < rect.centerx and hitbox.right > rect.left:
                    hitbox.right = rect.left - constants.ZERO
                    self.vel.x = constants.ZERO
                    self.input_dir.x = 0
                    do_break = True
                elif hitbox.left > rect.centerx and hitbox.left < rect.right:
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
                if hitbox.bottom < rect.centery and hitbox.bottom > rect.top:
                    hitbox.bottom = rect.top
                    self.vel.y = 0
                    self.input_dir.y = 0
                    do_break = True
                elif hitbox.top > rect.centery and hitbox.top < rect.bottom:
                    hitbox.top = rect.bottom
                    self.vel.y = 0
                    do_break = True
                if do_break:
                    self.pos.y += hitbox.y - prev_hitbox.y
                    break
