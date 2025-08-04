# 2. Egyedi sebességek használata mozgáshoz
# Frissítsd az összes ellenség x koordinátáját a saját sebességével, így mindenki máshogy mozog!

import pygame
import random

# Általános beállítások
WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 5
BULLET_SPEED = 10
ROWS, COLS = 4, 5
ENEMY_PADDING_X = 10
ENEMY_PADDING_Y = 25
ENEMY_SCALE = 0.15
ENEMY_OFFSET_X = 80
ENEMY_OFFSET_Y = 30
ENEMY_START_COUNT = 8


def generate_enemy_positions(rows, cols, offset_x, offset_y, padding_x, padding_y, enemy_width, enemy_height):
    positions = []
    for row in range(rows):
        for col in range(cols):
            x = offset_x + col * (enemy_width + padding_x)
            y = offset_y + row * (enemy_height + padding_y)
            positions.append((x, y))
    return positions


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


def move_player(rect, keys, speed):
    if keys[pygame.K_LEFT]:
        rect.x -= speed
    if keys[pygame.K_RIGHT]:
        rect.x += speed
    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, WIDTH)


def move_bullets(bullets, speed):
    for b in bullets:
        b[1] -= speed
    bullets[:] = [b for b in bullets if b[1] > 0]


def create_enemies(enemy_img, all_positions, count):
    random.shuffle(all_positions)
    selected = all_positions[:count]
    enemies = []
    for pos in selected:
        rect = enemy_img.get_rect(topleft=pos)
        enemy = {
    "rect": rect,
    "speed": random.uniform(1.0, 2.0),
    "color": (255, 255, 255),
    "image": enemy_img
}
        enemies.append(enemy)
    return enemies


def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    return True


def update_game_state(keys, player_rect, bullets, enemies, enemy_img, all_positions, level_data):
    current_time = pygame.time.get_ticks()
    move_player(player_rect, keys, PLAYER_SPEED)

    if keys[pygame.K_SPACE] and current_time - level_data["last_shot_time"] > level_data["shoot_delay"]:
        bullets.append([player_rect.centerx, player_rect.top])
        level_data["last_shot_time"] = current_time

    move_bullets(bullets, BULLET_SPEED)

    for bullet in bullets[:]:
        for enemy in enemies[:]:
            if enemy["rect"].collidepoint(bullet):
                bullets.remove(bullet)
                enemies.remove(enemy)
                break

    if not enemies:
        level_data["level"] += 1
        level_data["enemy_count"] = ENEMY_START_COUNT + (level_data["level"] - 1) * 2
        max_enemies = min(level_data["enemy_count"], ROWS * COLS)
        enemies[:] = create_enemies(enemy_img, all_positions.copy(), max_enemies)
        bullets.clear()
        player_rect.midbottom = (WIDTH // 2, HEIGHT)
        level_data["dx"] = 2

    move_down = False
    for enemy in enemies:
        enemy["rect"].x += int(level_data["dx"] * enemy["speed"])
        if enemy["rect"].right >= WIDTH or enemy["rect"].left <= 0:
            move_down = True

    if move_down:
        level_data["dx"] *= -1.1
        for enemy in enemies:
            enemy["rect"].y += level_data["descent"]


def draw_game(screen, player_img, player_rect, enemies, bullets, level):
    screen.fill((0, 0, 0))

    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, 5)

    for enemy in enemies:
        screen.blit(enemy["image"], enemy["rect"])

    screen.blit(player_img, player_rect)

    font = pygame.font.SysFont(None, 36)
    level_text = font.render(f"Level {level}", True, (255, 255, 255))
    screen.blit(level_text, (10, 10))

    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    player_img, player_rect = load_player()
    enemy_img = load_enemy()
    enemy_width = enemy_img.get_width()
    enemy_height = enemy_img.get_height()

    all_positions = generate_enemy_positions(
        ROWS, COLS,
        ENEMY_OFFSET_X, ENEMY_OFFSET_Y,
        ENEMY_PADDING_X, ENEMY_PADDING_Y,
        enemy_width, enemy_height
    )

    level_data = {
        "level": 1,
        "enemy_count": ENEMY_START_COUNT,
        "last_shot_time": 0,
        "shoot_delay": 1000,
        "dx": 2,
        "descent": 20
    }

    enemies = create_enemies(enemy_img, all_positions.copy(), level_data["enemy_count"])
    bullets = []

    running = True
    while running:
        running = handle_events()
        keys = pygame.key.get_pressed()
        update_game_state(keys, player_rect, bullets, enemies, enemy_img, all_positions, level_data)
        draw_game(screen, player_img, player_rect, enemies, bullets, level_data["level"])
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
