# 3. Széldetektálás és irányváltás, süllyedés
# Ha bármelyik ellenség eléri a bal vagy jobb szélt, az egész flotta visszafordul
# (dx = -dx), és minden ellenség y koordinátáját növeled (azaz lejjebb süllyednek).

import pygame

# Általános beállítások
WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 5
BULLET_SPEED = 10
ROWS, COLS = 5, 6
ENEMY_PADDING_X = 10
ENEMY_PADDING_Y = 25
ENEMY_SCALE = 0.15
ENEMY_OFFSET_X = 80
ENEMY_OFFSET_Y = 30

def load_player():
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT)
    return img, rect

def load_enemy():
    img = pygame.image.load("enemy_spinvaders.png").convert_alpha()
    scaled_width = int(img.get_width() * ENEMY_SCALE)
    scaled_height = int(img.get_height() * ENEMY_SCALE)
    img = pygame.transform.smoothscale(img, (scaled_width, scaled_height))
    return img

def create_enemy_grid(enemy_img, rows, cols, offset_x, offset_y, padding_x=10, padding_y=10):
    enemies = []
    enemy_width = enemy_img.get_width()
    enemy_height = enemy_img.get_height()
    spacing_x = enemy_width + padding_x
    spacing_y = enemy_height + padding_y

    total_width = cols * enemy_width + (cols - 1) * padding_x

    for row in range(rows):
        for col in range(cols):
            rect = enemy_img.get_rect()
            rect.topleft = (
                offset_x + col * spacing_x,
                offset_y + row * spacing_y
            )
            enemies.append(rect)
    return enemies

def move_player(rect, keys, speed):
    if keys[pygame.K_LEFT]:
        rect.x -= speed
    if keys[pygame.K_RIGHT]:
        rect.x += speed
    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, WIDTH)

def shoot(keys, rect, bullets):
    if keys[pygame.K_SPACE]:
        bullets.append([rect.centerx, rect.top])

def move_bullets(bullets, speed):
    for b in bullets:
        b[1] -= speed
    bullets[:] = [b for b in bullets if b[1] > 0]

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    player_img, player_rect = load_player()
    enemy_img = load_enemy()

    enemies = create_enemy_grid(
        enemy_img, ROWS, COLS,
        ENEMY_OFFSET_X, ENEMY_OFFSET_Y,
        ENEMY_PADDING_X, ENEMY_PADDING_Y
    )

    bullets = []
    dx = 2
    descent = 20

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        move_player(player_rect, keys, PLAYER_SPEED)
        shoot(keys, player_rect, bullets)
        move_bullets(bullets, BULLET_SPEED)

        move_down = False
        for enemy in enemies:
            enemy.x += dx
            if enemy.right >= WIDTH or enemy.left <= 0:
                move_down = True

        if move_down:
            dx *= -1
            for enemy in enemies:
                enemy.y += descent

        screen.fill((0, 0, 0))
        screen.blit(player_img, player_rect)

        for b in bullets:
            pygame.draw.circle(screen, (255, 255, 255), b, 5)

        for enemy_rect in enemies:
            screen.blit(enemy_img, enemy_rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
