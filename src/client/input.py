import pygame

from src import mailbox
from src.client import god


class Input:
    def __init__(self):
        god.input = self
        self.input_dir = pygame.Vector2()
        self.mouse_screen = pygame.Vector2()
        self.mouse_world = pygame.Vector2()
        # temp connect to server
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))

    def event(self, event: pygame.Event):
        if event.type == pygame.MOUSEWHEEL:
            god.world.camera.zoom_event(event.y)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSLASH:
                god.rendering.debug = not god.rendering.debug
        if event.type == pygame.MOUSEBUTTONUP:
            god.client.conn.mail(
                mailbox.MAIL_INPUT_EVENT, input_type=event.type, button=event.button
            )
        if event.type == pygame.MOUSEBUTTONDOWN:
            if god.ui.inventory_open:
                god.ui.mouse_clicked(event)
            if god.ui.can_interact_world():
                god.client.conn.mail(
                    mailbox.MAIL_INPUT_EVENT, input_type=event.type, button=event.button
                )
        if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
            if False:
                god.client.conn.mail(mailbox.MAIL_INPUT_EVENT, input_type=event.type)
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_e:
                god.ui.toggle_inventory()
            if event.key == pygame.K_ESCAPE:
                if god.ui.inventory_open:
                    god.ui.toggle_inventory()
            if event.key == pygame.K_q:
                if god.ui.inventory_open:
                    god.ui.inventory.floating_slot.source_slot = None

    def frame(self):
        self.mouse_screen = pygame.Vector2(pygame.mouse.get_pos())
        mouse_world = pygame.Vector2(self.mouse_world)
        self.mouse_world = god.camera.from_screen(self.mouse_screen)
        input_dir = pygame.Vector2()
        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            input_dir.x = -1
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            input_dir.x = 1
        if pressed[pygame.K_SPACE] or pressed[pygame.K_w] or pressed[pygame.K_UP]:
            input_dir.y = -1
        if input_dir != self.input_dir:
            self.input_dir = input_dir
            god.player.running = abs(self.input_dir.x) > 1e-3
            god.client.conn.mail(mailbox.MAIL_INPUT_DIR, dir=tuple(input_dir))
        if mouse_world != self.mouse_world:
            god.client.conn.mail(mailbox.MAIL_MOUSE_POS, pos=tuple(self.mouse_world))
