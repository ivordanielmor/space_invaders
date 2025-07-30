# 1. Ablak és fő ciklus indítása
# Elsőként indítsd el a Pygame-et, hozz létre egy 800×600-as ablakot,
# és egy végtelen game loop-ot, amely minden frame-ben frissíti a képernyőt.

import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((100, 200, 200))
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
