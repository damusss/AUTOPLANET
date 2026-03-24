import pygame

pygame.init()
win = pygame.Window(mouse_grabbed=False)
scr = win.get_surface()

while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            exit()
        if e.type == pygame.MOUSEMOTION:
            print(e)
        if e.type == pygame.KEYDOWN:
            pygame.mouse.set_pos(pos=(100, 100))

    scr.fill("black")
    win.flip()
