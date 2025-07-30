# 2. Játékos sprite betöltése és kezdeti pozíció
# Tölts be egy „player.png” nevű képet (sprite-ot),
# majd állítsd középre a képernyő alján.

import pygame
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))

player_image = pygame.image.load("player.png").convert_alpha()

original_width, original_height = player_image.get_size()

scale_factor = 2
new_size = (original_width * scale_factor, original_height * scale_factor)
player_image = pygame.transform.smoothscale(player_image, new_size)

player_rect = player_image.get_rect()
player_rect.midbottom = (WIDTH // 2, HEIGHT)

clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0,0,0))
    screen.blit(player_image, player_rect)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
