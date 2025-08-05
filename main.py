# 2. Életvesztés – Game Over logika
# Ha az ellenség eltalálja a játékost, vagy más hiba történik, csökkentsd a lives értékét.
# Ellenőrizd, hogy elfogytak-e az életek, és ha igen, állítsd le a játékot!

import pygame
import random

# Általános beállítások
WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 5
BULLET_SPEED = 10
ROWS, COLS = 4, 5
ENEMY_PADDING_X = 10
ENEMY_PADDING_Y = 25
ENEMY_OFFSET_X = 80
ENEMY_OFFSET_Y = 30
ENEMY_START_COUNT = 8
LIVES = 3

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
    return img

def tint_image(image, tint_color):
    tinted_image = image.copy()
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            pixel = image.get_at((x, y))
            if pixel.a != 0:
                tinted_image.set_at((x, y), pygame.Color(
                    tint_color[0], tint_color[1], tint_color[2], pixel.a))
    return tinted_image

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
    enemies = []
    for pos in all_positions[:count]:
        size = random.randint(20, 40)
        scaled_img = pygame.transform.smoothscale(enemy_img, (size, size))

        color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        )
        tinted_img = tint_image(scaled_img, color)
        rect = tinted_img.get_rect(topleft=pos)

        enemy = {
            "rect": rect,
            "speed": random.uniform(1.0, 2.0),
            "image": tinted_img,
            "size": size
        }
        enemies.append(enemy)
    return enemies

def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    return True

def update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives):
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
        enemies[:] = create_enemies(level_data["enemy_img"], all_positions.copy(), max_enemies)
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

    for enemy in enemies:
        if enemy["rect"].colliderect(player_rect):
            lives -= 1
            enemies.clear()
            bullets.clear()
            player_rect.midbottom = (WIDTH // 2, HEIGHT)
            level_data["dx"] = 2
            break

    game_over = lives <= 0
    return lives, game_over

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

    all_positions = generate_enemy_positions(
        ROWS, COLS,
        ENEMY_OFFSET_X, ENEMY_OFFSET_Y,
        ENEMY_PADDING_X, ENEMY_PADDING_Y,
        20, 20
    )

    level_data = {
        "level": 1,
        "enemy_count": ENEMY_START_COUNT,
        "last_shot_time": 0,
        "shoot_delay": 1000,
        "dx": 2,
        "descent": 20,
        "enemy_img": enemy_img
    }

    enemies = create_enemies(enemy_img, all_positions.copy(), level_data["enemy_count"])
    bullets = []
    lives = LIVES

    running = True
    while running:
        running = handle_events()
        keys = pygame.key.get_pressed()
        lives, game_over = update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives)
        if game_over:
            print("Game Over!")
            running = False
        draw_game(screen, player_img, player_rect, enemies, bullets, level_data["level"])
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
