import pygame
import random

# --- Globális beállítások ---
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

# Debug
DEBUG = False
LOG_EVERY_MS = 400
_last_log = 0
_last_action = None

# Állapot
last_move_direction = "right"  # alap vízszintes irány

# --- Segédosztályok és segédfüggvények ---

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
    rect.midbottom = (WIDTH // 2, HEIGHT - 50)
    return img, rect

def load_enemy():
    return pygame.image.load("enemy_spinvaders.png").convert_alpha()

def load_heart():
    img = pygame.image.load("heart.png").convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))

def move_player(rect, keys, ai_action=None):
    if ai_action and ai_action["move"]:
        mv = ai_action["move"]
        if mv in ("left", "right"):
            rect.x += PLAYER_SPEED * (-1 if mv == "left" else 1)
        elif mv in ("down", "retreat"):
            rect.y += PLAYER_SPEED
    else:
        if keys[pygame.K_LEFT]:
            rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            rect.x += PLAYER_SPEED
        if keys[pygame.K_DOWN]:
            rect.y += PLAYER_SPEED

    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, WIDTH)
    rect.top = max(rect.top, 0)
    rect.bottom = min(rect.bottom, HEIGHT)

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
    player_rect.midbottom = (WIDTH // 2, HEIGHT - 50)
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

def handle_shooting(keys, bullets, player_rect, current_time, level_data, shoot_delay, ai_action=None):
    should_shoot = False
    if ai_action and ai_action["shoot"]:
        should_shoot = True
    elif keys[pygame.K_SPACE]:
        should_shoot = True

    if should_shoot and current_time - level_data["last_shot_time"] > shoot_delay:
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
    close_distance = 70
    jump_chance_far = 0.010
    jump_chance_close = 0.15
    threshold = 200

    for enemy in enemies:
        dx = player_rect.centerx - (enemy["float_x"] + enemy["rect"].width / 2)
        dy = player_rect.centery - (enemy["float_y"] + enemy["rect"].height / 2)
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < close_distance:
            if random.random() < jump_chance_close:
                enemy["float_x"] += random.choice([-jump_distance, jump_distance])
                enemy["float_y"] += random.choice([-jump_distance, jump_distance])
        elif random.random() < jump_chance_far:
            if random.choice([True, False]):
                enemy["float_x"] -= jump_distance
            else:
                enemy["float_x"] += jump_distance
            enemy["float_y"] += enemy_speed_y
        else:
            if distance > threshold:
                if dx > 0:
                    enemy["float_x"] += enemy_speed_x
                elif dx < 0:
                    enemy["float_x"] -= enemy_speed_x
                enemy["float_y"] += enemy_speed_y

        enemy_width = enemy["rect"].width
        enemy_height = enemy["rect"].height
        enemy["float_x"] = max(0, min(WIDTH - enemy_width, enemy["float_x"]))
        enemy["float_y"] = max(0, min(HEIGHT - enemy_height, enemy["float_y"]))

        enemy["rect"].x = int(enemy["float_x"])
        enemy["rect"].y = int(enemy["float_y"])

        if distance < 100:
            color = (255, 0, 0)
        elif distance <= 250:
            color = (255, 255, 0)
        else:
            color = (0, 255, 0)

        base_img = pygame.transform.smoothscale(level_data["enemy_img"], (enemy_width, enemy_height))
        enemy["image"] = tint_image(base_img, color)

def check_player_collision(player_rect, enemies):
    return any(enemy["rect"].colliderect(player_rect) for enemy in enemies)

def _log_throttled(msg, action):
    global _last_log, _last_action
    if not DEBUG:
        return
    now = pygame.time.get_ticks()
    if (now - _last_log > LOG_EVERY_MS) and (action != _last_action):
        print(msg)
        _last_log = now
        _last_action = dict(action)

def _nearest_star(player_rect, powerups):
    stars = [p for p in powerups if p.type == "star"]
    if not stars:
        return None
    return min(stars, key=lambda p: abs(p.rect.centerx - player_rect.centerx))

def _enemy_metrics(player_rect, enemies):
    if not enemies:
        return None, None, None
    e = min(enemies, key=lambda en: ((en["rect"].centerx - player_rect.centerx) ** 2 +
                                     (en["rect"].centery - player_rect.centery) ** 2) ** 0.5)
    dx = e["rect"].centerx - player_rect.centerx
    dist = (dx ** 2 + (e["rect"].centery - player_rect.centery) ** 2) ** 0.5
    return e, dx, dist

def _decide_move_attack(dx, dist):
    global last_move_direction
    if dist < 120:
        mv = "left" if dx > 0 else "right"
        last_move_direction = mv
        return mv
    else:
        if dx < -10:
            last_move_direction = "left"
            return "left"
        elif dx > 10:
            last_move_direction = "right"
            return "right"
    return None

def decide_action(player_rect, enemies, powerups):
    global last_move_direction
    action = {"move": None, "shoot": False}

    star = _nearest_star(player_rect, powerups)
    if star:
        dx = star.rect.centerx - player_rect.centerx
        if dx < -5:
            action["move"] = "left";  last_move_direction = "left"
        elif dx > 5:
            action["move"] = "right"; last_move_direction = "right"
        if abs(dx) <= 15:
            action["shoot"] = True
        _log_throttled(f"Powerup chase, action: {action}", action)
        return action

    enemy, dx, dist = _enemy_metrics(player_rect, enemies)
    if enemy is not None:
        if dist < 150:
            action["move"] = "retreat"
            if abs(dx) <= 25:
                action["shoot"] = True
            _log_throttled(f"Retreat, d={dist:.1f}, action: {action}", action)
            return action

        action["move"] = _decide_move_attack(dx, dist)
        if abs(dx) <= 25:
            action["shoot"] = True
        _log_throttled(f"Enemy decision, d={dist:.1f}, dx={dx:.1f}, action: {action}", action)

    if action["move"] is None:
        action["move"] = last_move_direction

    _log_throttled(f"Default move, action: {action}", action)
    return action

def update_game_state(keys, player_rect, bullets, enemies, all_positions, level_data, lives, score, powerups, player_powerups, ai_mode):
    current_time = pygame.time.get_ticks()
    ai_action = decide_action(player_rect, enemies, powerups) if ai_mode else None

    move_player(player_rect, keys, ai_action if ai_mode else None)
    spawn_powerup(powerups)
    shoot_delay = update_shoot_delay(player_powerups)
    handle_shooting(keys, bullets, player_rect, current_time, level_data, shoot_delay, ai_action if ai_mode else None)
    move_bullets(bullets)
    score = handle_bullet_collisions(bullets, enemies, powerups, score, player_powerups)
    remove_expired_powerups(powerups)
    collect_powerups(player_rect, powerups, player_powerups)
    move_enemies(enemies, level_data, player_rect)

    SAFE_BASELINE = HEIGHT - 50
    if ai_mode and player_rect.bottom > SAFE_BASELINE:
        player_rect.y -= 1

    if check_player_collision(player_rect, enemies):
        lives -= 1
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
    elif not enemies:
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False)

    return lives, lives <= 0, score