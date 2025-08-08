# 2. Véletlenszerű power-up spawn és ütközés
# Minden frame-ben kis eséllyel jelenjen meg új power-up, és ellenőrizd az ütközést:

import pygame
import random
import sys

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
COMBO_RADIUS = 50

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, image_path, type, position, duration_ms):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.smoothscale(self.image, (32, 32))
        self.rect = self.image.get_rect(center=position)
        self.type = type
        self.spawn_time = pygame.time.get_ticks()
        self.duration = duration_ms

    def is_active(self):
        current_time = pygame.time.get_ticks()
        return (current_time - self.spawn_time) < self.duration

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
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
    return True

def reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False):
    if not same_level:
        level_data["level"] += 1
        level_data["enemy_count"] = ENEMY_START_COUNT + (level_data["level"] - 1) * 2
    max_enemies = min(level_data["enemy_count"], ROWS * COLS)
    enemies[:] = create_enemies(level_data["enemy_img"], all_positions.copy(), max_enemies)
    bullets.clear()
    player_rect.midbottom = (WIDTH // 2, HEIGHT)
    level_data["dx"] = 2

def update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives, score, powerups, player_powerups):
    current_time = pygame.time.get_ticks()
    move_player(player_rect, keys, PLAYER_SPEED)

    if len(powerups) == 0 and random.random() < 0.005:
        pos = (random.randint(50, WIDTH-50), random.randint(50, HEIGHT-150))
        powerup = PowerUp("star.png", "star", pos, 4000)
        powerups.add(powerup)

    if keys[pygame.K_SPACE] and current_time - level_data["last_shot_time"] > level_data["shoot_delay"]:
        bullets.append([player_rect.centerx, player_rect.top])
        level_data["last_shot_time"] = current_time

    move_bullets(bullets, BULLET_SPEED)

    for bullet in bullets[:]:
        hit_powerup = False
        for powerup in powerups:
            if powerup.rect.collidepoint(bullet):
                powerups.remove(powerup)
                if bullet in bullets:
                    bullets.remove(bullet)
                hit_powerup = True
                break
        if hit_powerup:
            continue

        for enemy in enemies[:]:
            if enemy["rect"].collidepoint(bullet):
                bullets.remove(bullet)
                nearby_count = 0
                ex, ey = enemy["rect"].center
                for other in enemies:
                    if other is enemy:
                        continue
                    ox, oy = other["rect"].center
                    dist = ((ex - ox) ** 2 + (ey - oy) ** 2) ** 0.5
                    if dist <= COMBO_RADIUS:
                        nearby_count += 1
                if nearby_count > 0:
                    score += 20
                else:
                    score += 10
                enemies.remove(enemy)
                break

    for powerup in list(powerups):
        if not powerup.is_active():
            powerups.remove(powerup)

    for powerup in list(powerups):
        if player_rect.colliderect(powerup.rect):
            player_powerups[powerup.type] = pygame.time.get_ticks()
            powerups.remove(powerup)

    player_died = False
    for enemy in enemies:
        enemy["rect"].x += int(level_data["dx"] * enemy["speed"])
        if enemy["rect"].right >= WIDTH or enemy["rect"].left <= 0:
            for e in enemies:
                e["rect"].y += level_data["descent"]
            level_data["dx"] *= -1.1
            break

    for enemy in enemies:
        if enemy["rect"].colliderect(player_rect):
            lives -= 1
            player_died = True
            break

    if player_died:
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
    elif not enemies:
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False)

    game_over = lives <= 0 or len(enemies) == 0
    return lives, game_over, score

def draw_game(screen, player_img, player_rect, enemies, bullets, powerups, level, lives, heart_img, score):
    screen.fill((0, 0, 0))

    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, 5)

    for enemy in enemies:
        screen.blit(enemy["image"], enemy["rect"])

    powerups.draw(screen)

    screen.blit(player_img, player_rect)

    font = pygame.font.SysFont(None, 36)
    level_text = font.render(f"Level {level}", True, (255, 255, 255))
    screen.blit(level_text, (10, 10))

    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(score_text, (WIDTH - score_text.get_width() - 10, 10))

    for i in range(lives):
        screen.blit(heart_img, (10 + i * 34, 50))

    pygame.display.flip()

def draw_game_over(screen):
    screen.fill((0, 0, 0))
    big_font = pygame.font.SysFont(None, 72)
    font = pygame.font.SysFont(None, 36)

    text1 = big_font.render("GAME OVER", True, (255, 0, 0))
    text2 = font.render("Nyomj ENTER-t az újrakezdéshez", True, (255, 255, 255))
    text3 = font.render("Kilépéshez nyomj ESC-t", True, (200, 200, 200))

    screen.blit(text1, ((WIDTH - text1.get_width()) // 2, HEIGHT // 2 - 80))
    screen.blit(text2, ((WIDTH - text2.get_width()) // 2, HEIGHT // 2 + 10))
    screen.blit(text3, ((WIDTH - text3.get_width()) // 2, HEIGHT // 2 + 50))

    pygame.display.flip()

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    heart_img = pygame.image.load("heart.png").convert_alpha()
    heart_img = pygame.transform.smoothscale(heart_img, (32, 32))

    while True:
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
        score = 0
        powerups = pygame.sprite.Group()
        player_powerups = {}

        running = True
        game_over = False

        while running:
            running = handle_events()
            keys = pygame.key.get_pressed()
            lives, game_over, score = update_game_state(
                keys, player_rect, bullets, enemies, all_positions, level_data, lives, score, powerups, player_powerups)

            if game_over:
                break

            draw_game(screen, player_img, player_rect, enemies, bullets, powerups, level_data["level"], lives, heart_img, score)
            clock.tick(60)

        draw_game_over(screen)
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        waiting = False
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

if __name__ == "__main__":
    main()
