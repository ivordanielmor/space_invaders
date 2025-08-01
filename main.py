# 2. Grid (tömbös) elrendezés létrehozása
# Használj beágyazott for-ciklust, hogy
# több sort és oszlopot generálj. Minden sprite-hoz számold ki az x/y
# koordinátát a sor és oszlop alapján, majd adj hozzá egy új rect-et a listához!

import pygame

# Általános beállítások
WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 5
BULLET_SPEED = 10
ROWS, COLS = 5, 10
ENEMY_SPACING_X = 60
ENEMY_SPACING_Y = 50
ENEMY_OFFSET_X = 100
ENEMY_OFFSET_Y = 50

def load_player():
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT)
    return img, rect

def load_enemy():
    img = pygame.image.load("enemy_spinvaders.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    return img

def create_enemy_grid(enemy_img, rows, cols, spacing_x, spacing_y, offset_x, offset_y):
    enemies = []
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
    pygame.display.set_caption("Space Invaders - 2. feladat (csak grid)")
    clock = pygame.time.Clock()

    player_img, player_rect = load_player()
    enemy_img = load_enemy()

    enemies = create_enemy_grid(
        enemy_img, ROWS, COLS,
        ENEMY_SPACING_X, ENEMY_SPACING_Y,
        ENEMY_OFFSET_X, ENEMY_OFFSET_Y
    )

    bullets = []
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        move_player(player_rect, keys, PLAYER_SPEED)
        shoot(keys, player_rect, bullets)
        move_bullets(bullets, BULLET_SPEED)

        screen.fill((0, 0, 0))
        screen.blit(player_img, player_rect)
        for b in bullets:
            pygame.draw.circle(screen, (255, 255, 255), b, 5)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
