# 3. Hatáskezelés – Power-up aktiválása és időzítés
# Az aktiválás során kapjon a játékos ideiglenes vagy végleges bónuszt:

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
BASE_SHOOT_DELAY = 1000
POWERUP_SHOOT_DELAY = 300

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
    return [
        (offset_x + col * (enemy_width + padding_x),
         offset_y + row * (enemy_height + padding_y))
        for row in range(rows) for col in range(cols)
    ]

def load_player():
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT)
    return img, rect

def load_enemy():
    return pygame.image.load("enemy_spinvaders.png").convert_alpha()

def load_heart():
    img = pygame.image.load("heart.png").convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))

def tint_image(image, tint_color):
    tinted_image = image.copy()
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            pixel = image.get_at((x, y))
            if pixel.a != 0:
                tinted_image.set_at((x, y), pygame.Color(*tint_color, pixel.a))
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
        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        tinted_img = tint_image(scaled_img, color)
        rect = tinted_img.get_rect(topleft=pos)
        enemies.append({
            "rect": rect,
            "speed": random.uniform(1.0, 2.0),
            "image": tinted_img,
            "size": size
        })
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

def spawn_powerup(powerups):
    if len(powerups) == 0 and random.random() < 0.001:
        pos = (random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 150))
        powerup = PowerUp("star.png", "star", pos, 4000)
        powerups.add(powerup)

def update_shoot_delay(player_powerups, current_time):
    if "star" in player_powerups:
        if current_time - player_powerups["star"] < 4000:
            return POWERUP_SHOOT_DELAY
        else:
            del player_powerups["star"]
    return BASE_SHOOT_DELAY

def handle_shooting(keys, bullets, player_rect, current_time, level_data, shoot_delay):
    if keys[pygame.K_SPACE] and current_time - level_data["last_shot_time"] > shoot_delay:
        bullets.append([player_rect.centerx, player_rect.top])
        level_data["last_shot_time"] = current_time

def handle_bullet_collisions(bullets, enemies, powerups, score, player_powerups):
    for bullet in bullets[:]:
        for powerup in powerups:
            if powerup.rect.collidepoint(bullet):
                powerups.remove(powerup)
                if bullet in bullets:
                    bullets.remove(bullet)
                player_powerups[powerup.type] = pygame.time.get_ticks()
                break
        else:
            for enemy in enemies[:]:
                if enemy["rect"].collidepoint(bullet):
                    bullets.remove(bullet)
                    ex, ey = enemy["rect"].center
                    nearby_count = sum(
                        1 for other in enemies if other is not enemy and
                        ((ex - other["rect"].centerx) ** 2 + (ey - other["rect"].centery) ** 2) ** 0.5 <= COMBO_RADIUS
                    )
                    score += 20 if nearby_count > 0 else 10
                    enemies.remove(enemy)
                    break
    return score

def remove_expired_powerups(powerups):
    for powerup in list(powerups):
        if not powerup.is_active():
            powerups.remove(powerup)

def collect_powerups(player_rect, powerups, player_powerups):
    for powerup in list(powerups):
        if player_rect.colliderect(powerup.rect):
            player_powerups[powerup.type] = pygame.time.get_ticks()
            powerups.remove(powerup)

def move_enemies(enemies, level_data):
    for enemy in enemies:
        enemy["rect"].x += int(level_data["dx"] * enemy["speed"])
    if any(enemy["rect"].right >= WIDTH or enemy["rect"].left <= 0 for enemy in enemies):
        for e in enemies:
            e["rect"].y += level_data["descent"]
        level_data["dx"] *= -1.1

def check_player_collision(player_rect, enemies):
    return any(enemy["rect"].colliderect(player_rect) for enemy in enemies)

def update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives, score, powerups, player_powerups):
    current_time = pygame.time.get_ticks()
    move_player(player_rect, keys, PLAYER_SPEED)
    spawn_powerup(powerups)

    shoot_delay = update_shoot_delay(player_powerups, current_time)
    handle_shooting(keys, bullets, player_rect, current_time, level_data, shoot_delay)
    move_bullets(bullets, BULLET_SPEED)

    score = handle_bullet_collisions(bullets, enemies, powerups, score, player_powerups)
    remove_expired_powerups(powerups)
    collect_powerups(player_rect, powerups, player_powerups)
    move_enemies(enemies, level_data)

    player_died = check_player_collision(player_rect, enemies)
    if player_died:
        lives -= 1
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
    elif not enemies:
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False)

    game_over = lives <= 0 or len(enemies) == 0
    return lives, game_over, score

def draw_bullets(screen, bullets):
    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, 5)

def draw_enemies(screen, enemies):
    for enemy in enemies:
        screen.blit(enemy["image"], enemy["rect"])

def draw_ui(screen, level, lives, heart_img, score):
    font = pygame.font.SysFont(None, 36)
    level_text = font.render(f"Level {level}", True, (255, 255, 255))
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(level_text, (10, 10))
    screen.blit(score_text, (WIDTH - score_text.get_width() - 10, 10))
    for i in range(lives):
        screen.blit(heart_img, (10 + i * 34, 50))

def draw_game(screen, player_img, player_rect, enemies, bullets, powerups, level, lives, heart_img, score):
    screen.fill((0, 0, 0))
    draw_bullets(screen, bullets)
    draw_enemies(screen, enemies)
    powerups.draw(screen)
    screen.blit(player_img, player_rect)
    draw_ui(screen, level, lives, heart_img, score)
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

def initialize_game():
    player_img, player_rect = load_player()
    enemy_img = load_enemy()
    heart_img = load_heart()
    all_positions = generate_enemy_positions(ROWS, COLS, ENEMY_OFFSET_X, ENEMY_OFFSET_Y, ENEMY_PADDING_X, ENEMY_PADDING_Y, 20, 20)
    level_data = {
        "level": 1,
        "enemy_count": ENEMY_START_COUNT,
        "last_shot_time": 0,
        "shoot_delay": BASE_SHOOT_DELAY,
        "dx": 2,
        "descent": 20,
        "enemy_img": enemy_img
    }
    enemies = create_enemies(enemy_img, all_positions.copy(), level_data["enemy_count"])
    bullets = []
    powerups = pygame.sprite.Group()
    player_powerups = {}
    score = 0
    lives = LIVES
    return player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img, powerups, player_powerups, score, lives

def game_loop(screen, clock):
    (player_img, player_rect, enemies, bullets, all_positions, level_data,
     heart_img, powerups, player_powerups, score, lives) = initialize_game()

    running = True
    while running:
        running = handle_events()
        keys = pygame.key.get_pressed()
        lives, game_over, score = update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives, score, powerups, player_powerups)
        if game_over:
            break
        draw_game(screen, player_img, player_rect, enemies, bullets, powerups, level_data["level"], lives, heart_img, score)
        clock.tick(60)
    return True

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    while True:
        game_loop(screen, clock)
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
