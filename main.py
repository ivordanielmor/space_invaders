# HÁZI FELADAT
# Tedd még nehezebbé: – Időnként minden ellenség "ugorjon" egyet, de ha már
# nagyon közel vannak (<70px), legyen esély rá, hogy teljesen random irányba
# lépnek (pl. akár el is kerülik a játékost).
# – Kísérletezz: próbáld ki, mennyire lesz izgalmasabb,
# ha az ugrás esélyét és nagyságát változtatod!

import sys
import pygame
from helper import *  # egyszerű a tanulónak; minden konstans és függvény jön

def draw_ui(screen, level, lives, heart_img, score, ai_mode):
    font = pygame.font.SysFont(None, 36)
    screen.blit(font.render(f"Level {level}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (WIDTH - 150, 10))
    mode_text = "AI Mód" if ai_mode else "Játékos Mód"
    mode_color = (0, 255, 0) if ai_mode else (255, 255, 0)
    mode_surface = font.render(f"{mode_text} (M = váltás)", True, mode_color)
    screen.blit(mode_surface, (10, HEIGHT - 40))
    for i in range(lives):
        screen.blit(heart_img, (10 + i * 34, 50))

def draw_game(screen, player_img, player_rect, enemies, bullets, powerups, level, lives, heart_img, score, ai_mode):
    screen.fill((0, 0, 0))
    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, 5)
    for e in enemies:
        screen.blit(e["image"], e["rect"])
    powerups.draw(screen)
    screen.blit(player_img, player_rect)
    draw_ui(screen, level, lives, heart_img, score, ai_mode)
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
        lives = 5; enemy_count = 6; speed_multiplier = 0.8
    elif difficulty_index == 1:
        lives = 3; enemy_count = 8; speed_multiplier = 1.0
    else:
        lives = 2; enemy_count = 10; speed_multiplier = 1.3

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

    ai_mode = False
    m_key_pressed = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_m] and not m_key_pressed:
            ai_mode = not ai_mode
            m_key_pressed = True
        elif not keys[pygame.K_m]:
            m_key_pressed = False

        lives, game_over, score = update_game_state(
            keys, player_rect, bullets, enemies, all_positions, level_data,
            lives, score, powerups, player_powerups, ai_mode
        )

        if game_over:
            draw_game_over(screen)
            pygame.time.wait(3000)
            return

        draw_game(screen, player_img, player_rect, enemies, bullets, powerups,
                  level_data["level"], lives, heart_img, score, ai_mode)
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
                pygame.quit(); sys.exit()
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
                        pygame.quit(); sys.exit()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
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
    