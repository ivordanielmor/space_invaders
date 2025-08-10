# 1. Több ellenség követése és "trükkös" mozgása
# Iteráld végig az enemies listát minden frame-ben, és minden ellenség:
# Ha szerencséje van (10% eséllyel), "ugrik" egy nagyot balra vagy jobbra, ezzel becsaphat!
# Különben if/else logikával követi a játékos X pozícióját.

import pygame
import sys
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
        return pygame.time.get_ticks() - self.spawn_time < self.duration

def tint_image(image, tint_color):
    tinted_image = image.copy()
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            pixel = image.get_at((x, y))
            if pixel.a != 0:
                tinted_image.set_at((x, y), pygame.Color(*tint_color, pixel.a))
    return tinted_image

def generate_enemy_positions():
    return [
        (ENEMY_OFFSET_X + col * (20 + ENEMY_PADDING_X),
         ENEMY_OFFSET_Y + row * (20 + ENEMY_PADDING_Y))
        for row in range(ROWS) for col in range(COLS)
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

def move_player(rect, keys):
    if keys[pygame.K_LEFT]:
        rect.x -= PLAYER_SPEED
    if keys[pygame.K_RIGHT]:
        rect.x += PLAYER_SPEED
    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, WIDTH)

def move_bullets(bullets):
    for b in bullets:
        b[1] -= BULLET_SPEED
    bullets[:] = [b for b in bullets if b[1] > 0]

def create_enemies(enemy_img, all_positions, count, speed_multiplier=1.0):
    random.shuffle(all_positions)
    enemies = []
    for pos in all_positions[:count]:
        size = random.randint(20, 40)
        scaled_img = pygame.transform.smoothscale(enemy_img, (size, size))
        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        tinted_img = tint_image(scaled_img, color)
        rect = tinted_img.get_rect(topleft=pos)
        speed = random.uniform(1.0, 2.0) * speed_multiplier
        enemies.append({
            "rect": rect,
            "speed": speed,
            "image": tinted_img,
            "float_x": float(rect.x),
            "float_y": float(rect.y),
        })
    return enemies

def reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False):
    if not same_level:
        level_data["level"] += 1
        level_data["enemy_count"] += 2
    enemies[:] = create_enemies(level_data["enemy_img"], all_positions, level_data["enemy_count"], level_data["speed_multiplier"])
    bullets.clear()
    player_rect.midbottom = (WIDTH // 2, HEIGHT)
    level_data["dx"] = 2 * level_data["speed_multiplier"]

def spawn_powerup(powerups):
    if len(powerups) == 0 and random.random() < 0.001:
        pos = (random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 150))
        powerup = PowerUp("star.png", "star", pos, 4000)
        powerups.add(powerup)

def update_shoot_delay(player_powerups):
    if "star" in player_powerups:
        if pygame.time.get_ticks() - player_powerups["star"] < 4000:
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
                    enemies.remove(enemy)
                    score += 10
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

def move_enemies(enemies, level_data, player_rect):
    enemy_speed_x = 1.2
    enemy_speed_y = 0.5
    jump_distance = 60
    threshold = 200

    for enemy in enemies:
        if random.random() < 0.010:
            if random.choice([True, False]):
                enemy["float_x"] -= jump_distance
            else:
                enemy["float_x"] += jump_distance
            enemy["float_y"] += enemy_speed_y
        else:
            dx = player_rect.centerx - (enemy["float_x"] + enemy["rect"].width / 2)
            dy = player_rect.centery - (enemy["float_y"] + enemy["rect"].height / 2)
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance > threshold:
                if dx > 0:
                    enemy["float_x"] += enemy_speed_x
                elif dx < 0:
                    enemy["float_x"] -= enemy_speed_x
                enemy["float_y"] += enemy_speed_y

        enemy_width = enemy["rect"].width
        enemy_height = enemy["rect"].height
        enemy["float_x"] = max(0, min(WIDTH - enemy_width, enemy["float_x"]))
        enemy["float_y"] = min(HEIGHT - enemy_height, enemy["float_y"])

        enemy["rect"].x = int(enemy["float_x"])
        enemy["rect"].y = int(enemy["float_y"])

def check_player_collision(player_rect, enemies):
    return any(enemy["rect"].colliderect(player_rect) for enemy in enemies)

def update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives, score, powerups, player_powerups):
    current_time = pygame.time.get_ticks()
    move_player(player_rect, keys)
    spawn_powerup(powerups)
    shoot_delay = update_shoot_delay(player_powerups)
    handle_shooting(keys, bullets, player_rect, current_time, level_data, shoot_delay)
    move_bullets(bullets)
    score = handle_bullet_collisions(bullets, enemies, powerups, score, player_powerups)
    remove_expired_powerups(powerups)
    collect_powerups(player_rect, powerups, player_powerups)
    move_enemies(enemies, level_data, player_rect)

    if check_player_collision(player_rect, enemies):
        lives -= 1
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
    elif not enemies:
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False)

    return lives, lives <= 0, score

def draw_ui(screen, level, lives, heart_img, score):
    font = pygame.font.SysFont(None, 36)
    screen.blit(font.render(f"Level {level}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (WIDTH - 150, 10))
    for i in range(lives):
        screen.blit(heart_img, (10 + i * 34, 50))

def draw_game(screen, player_img, player_rect, enemies, bullets, powerups, level, lives, heart_img, score):
    screen.fill((0, 0, 0))
    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, 5)
    for e in enemies:
        screen.blit(e["image"], e["rect"])
    powerups.draw(screen)
    screen.blit(player_img, player_rect)
    draw_ui(screen, level, lives, heart_img, score)
    pygame.display.flip()

def draw_game_over(screen):
    screen.fill((0, 0, 0))
    font = pygame.font.SysFont(None, 72)
    text = font.render("GAME OVER", True, (255, 0, 0))
    screen.blit(text, ((WIDTH - text.get_width()) // 2, HEIGHT // 2 - 40))
    pygame.display.flip()

def initialize_game(difficulty_index):
    player_img, player_rect = load_player()
    enemy_img = load_enemy()
    heart_img = load_heart()
    all_positions = generate_enemy_positions()

    if difficulty_index == 0:
        lives = 5
        enemy_count = 6
        speed_multiplier = 0.8
    elif difficulty_index == 1:
        lives = 3
        enemy_count = 8
        speed_multiplier = 1.0
    else:
        lives = 2
        enemy_count = 10
        speed_multiplier = 1.3

    level_data = {
        "level": 1,
        "enemy_count": enemy_count,
        "last_shot_time": 0,
        "dx": 2 * speed_multiplier,
        "enemy_img": enemy_img,
        "speed_multiplier": speed_multiplier
    }

    enemies = create_enemies(enemy_img, all_positions.copy(), enemy_count, speed_multiplier)
    bullets = []
    powerups = pygame.sprite.Group()
    player_powerups = {}
    score = 0

    return player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img, powerups, player_powerups, score, lives

def game_loop(screen, clock, difficulty_index):
    (player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img,
     powerups, player_powerups, score, lives) = initialize_game(difficulty_index)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

        keys = pygame.key.get_pressed()
        lives, game_over, score = update_game_state(keys, player_rect, bullets, enemies,
                                                    all_positions, level_data, lives, score,
                                                    powerups, player_powerups)
        if game_over:
            draw_game_over(screen)
            pygame.time.wait(3000)
            return

        draw_game(screen, player_img, player_rect, enemies, bullets, powerups,
                  level_data["level"], lives, heart_img, score)
        clock.tick(60)

def menu_loop(screen, clock):
    font = pygame.font.SysFont(None, 48)
    options = ["Indítás", "Nehézség: Normál", "Kilépés"]
    selected = 0
    difficulties = ["Könnyű", "Normál", "Nehéz"]
    difficulty_index = 1

    while True:
        screen.fill((0, 0, 0))
        for i, text in enumerate(options):
            color = (255, 255, 0) if i == selected else (255, 255, 255)
            label = font.render(text, True, color)
            screen.blit(label, ((WIDTH - label.get_width()) // 2, 200 + i * 60))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    if selected == 0:
                        return difficulty_index
                    elif selected == 1:
                        difficulty_index = (difficulty_index + 1) % len(difficulties)
                        options[1] = f"Nehézség: {difficulties[difficulty_index]}"
                    elif selected == 2:
                        pygame.quit()
                        sys.exit()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
        clock.tick(60)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    while True:
        difficulty_index = menu_loop(screen, clock)
        game_loop(screen, clock, difficulty_index)

if __name__ == "__main__":
    main()
