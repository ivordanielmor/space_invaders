# 3. Mozgatás balra/jobbra, szélek ellenőrzése
# Figyeld a balra/jobbra nyilakat! Minden frame-ben frissítsd a sprite
#  pozícióját, és akadályozd meg, hogy kimenjen a képernyő szélén túl.

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

player_speed = 5

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player_rect.x -= player_speed
    if keys[pygame.K_RIGHT]:
        player_rect.x += player_speed

    if player_rect.left < 0:
        player_rect.left = 0
    if player_rect.right > WIDTH:
        player_rect.right = WIDTH

    screen.fill((0, 0, 0))
    screen.blit(player_image, player_rect)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
