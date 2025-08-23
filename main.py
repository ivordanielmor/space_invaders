# 1) PATCH A – Adatgyűjtés a meglévő játékba (CSV)
# Cél: amikor kézzel irányítasz (AI OFF), minden billentyűleütéskor rögzítsünk egy példát. Így
# a modell a te játékstílusodat tanulja.
# A kódrészleteket a meglévő projekted megfelelő részeibe illeszd: a) importok, b)
# segédfüggvények, c) eseménykezelő (KEYDOWN).
# a) Új importok (a fájl tetején)
# b) Segédfüggvények (a többi def mellé)
# c) Eseménykezelésben (KEYDOWN) – csak kézi módban loggolunk

import sys
from typing import Tuple, List, Dict, Any
import pygame
from helper import *


def draw_ui(screen: pygame.Surface, level: int, lives: int,
            heart_img: pygame.Surface, score: int, ai_mode: bool) -> None:
    """Kirajzolja a felhasználói felületet: szint, pontszám, mód és életek.

    Paraméterek:
        screen (pygame.Surface): Célfelület, ahova rajzolunk.
        level (int): Aktuális szint száma.
        lives (int): Játékos hátralévő életeinek száma.
        heart_img (pygame.Surface): Élet ikon 32×32 körül.
        score (int): Aktuális pontszám.
        ai_mode (bool): True esetén AI-mód felirat, különben játékos mód.

    Visszatérés:
        None

    Mellékhatás:
        A `screen` felületre szövegek és ikonok kerülnek.
    """
    font = pygame.font.SysFont(None, 36)
    screen.blit(font.render(f"Level {level}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (WIDTH - 150, 10))
    mode_text = "AI Mód" if ai_mode else "Játékos Mód"
    mode_color = (0, 255, 0) if ai_mode else (255, 255, 0)
    mode_surface = font.render(f"{mode_text} (M = váltás)", True, mode_color)
    screen.blit(mode_surface, (10, HEIGHT - 40))
    for i in range(lives):
        screen.blit(heart_img, (10 + i * 34, 50))


def draw_game(screen: pygame.Surface, player_img: pygame.Surface, player_rect: pygame.Rect,
              enemies: List[Dict[str, Any]], bullets: List[List[int]],
              powerups: pygame.sprite.Group, level: int, lives: int,
              heart_img: pygame.Surface, score: int, ai_mode: bool) -> None:
    """Kirajzolja a teljes jelenetet: háttér, lövedékek, ellenségek, power-upok, játékos és UI.

    Paraméterek:
        screen (pygame.Surface): Célfelület.
        player_img (pygame.Surface): Játékos sprite.
        player_rect (pygame.Rect): Játékos helyzete.
        enemies (List[Dict]): Ellenségek állapota („image”, „rect” kulcsok kötelezők).
        bullets (List[List[int]]): Lövedékek [x, y] listája.
        powerups (pygame.sprite.Group): Aktív power-up sprite-ok.
        level (int): Szint száma.
        lives (int): Életek száma.
        heart_img (pygame.Surface): Élet ikon.
        score (int): Pontszám.
        ai_mode (bool): AI mód kijelzéséhez.

    Visszatérés:
        None

    Mellékhatás:
        Képernyő tartalma frissül és `pygame.display.flip()` meghívódik.
    """
    screen.fill((0, 0, 0))
    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, 5)
    for e in enemies:
        screen.blit(e["image"], e["rect"])
    powerups.draw(screen)
    screen.blit(player_img, player_rect)
    draw_ui(screen, level, lives, heart_img, score, ai_mode)
    pygame.display.flip()


def draw_game_over(screen: pygame.Surface) -> None:
    """Kirajzolja a „GAME OVER” képernyőt középre igazított felirattal.

    Paraméterek:
        screen (pygame.Surface): Célfelület.

    Visszatérés:
        None
    """
    screen.fill((0, 0, 0))
    font = pygame.font.SysFont(None, 72)
    text = font.render("GAME OVER", True, (255, 0, 0))
    screen.blit(text, ((WIDTH - text.get_width()) // 2, HEIGHT // 2 - 40))
    pygame.display.flip()


def initialize_game(difficulty_index: int
                    ) -> Tuple[pygame.Surface, pygame.Rect, List[Dict[str, Any]],
                               List[List[int]], List[Tuple[int, int]], Dict[str, Any],
                               pygame.Surface, pygame.sprite.Group, Dict[str, int],
                               int, int]:
    """Inicializálja a játék állapotát a választott nehézséggel.

    Paraméterek:
        difficulty_index (int): 0=Könnyű, 1=Normál, 2=Nehéz.

    Visszatérés:
        Tuple:
            player_img (Surface)
            player_rect (Rect)
            enemies (List[Dict])
            bullets (List[List[int]])
            all_positions (List[Tuple[int,int]])
            level_data (Dict[str,Any]): {"level","enemy_count","last_shot_time","dx","enemy_img","speed_multiplier"}
            heart_img (Surface)
            powerups (pygame.sprite.Group)
            player_powerups (Dict[str,int]): aktiválási idők
            score (int)
            lives (int)

    Kivétel dobása:
        pygame.error / FileNotFoundError: Sprite-ok betöltésekor.
    """
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

    level_data: Dict[str, Any] = {
        "level": 1,
        "enemy_count": enemy_count,
        "last_shot_time": 0,
        "dx": 2 * speed_multiplier,
        "enemy_img": enemy_img,
        "speed_multiplier": speed_multiplier
    }

    enemies = create_enemies(enemy_img, all_positions.copy(), enemy_count, speed_multiplier)
    bullets: List[List[int]] = []
    powerups = pygame.sprite.Group()
    player_powerups: Dict[str, int] = {}
    score = 0

    return (player_img, player_rect, enemies, bullets, all_positions,
            level_data, heart_img, powerups, player_powerups, score, lives)


def game_loop(screen: pygame.Surface, clock: pygame.time.Clock, difficulty_index: int) -> None:
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
            elif event.type == pygame.KEYDOWN and ai_mode == False:
                debug_print(f"Key pressed: {event.key}, enemies count: {len(enemies)}")  # Debug üzenet
                center = closest_enemy_center(player_rect, enemies)
                debug_print(f"Closest enemy center: {center}")  # Debug üzenet
                if center is not None:
                    cx, cy = center
                    dx = cx - player_rect.centerx
                    dy = cy - player_rect.centery
                    speed_multiplier = level_data["speed_multiplier"]
                    enemy_count = len(enemies)
                    if event.key == pygame.K_LEFT:
                        debug_print("Logging LEFT action")  # Debug üzenet
                        log_example(dx, dy, 0, speed_multiplier, enemy_count)
                    elif event.key == pygame.K_RIGHT:
                        debug_print("Logging RIGHT action")  # Debug üzenet
                        log_example(dx, dy, 1, speed_multiplier, enemy_count)
                    elif event.key == pygame.K_SPACE:
                        debug_print("Logging SPACE action")  # Debug üzenet
                        log_example(dx, dy, 2, speed_multiplier, enemy_count)
                else:
                    debug_print("No enemies, skipping log_example")  # Debug üzenet

        keys = pygame.key.get_pressed()
        if keys[pygame.K_m] and not m_key_pressed:
            ai_mode = not ai_mode
            m_key_pressed = True
            print(f"AI mode toggled: {ai_mode}")  # Debug üzenet
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


def menu_loop(screen: pygame.Surface, clock: pygame.time.Clock) -> int:
    """Főmenü ciklus. Elemválasztás és nehézség állítása.

    Paraméterek:
        screen (pygame.Surface): Kijelző felülete.
        clock (pygame.time.Clock): FPS kontroll.

    Visszatérés:
        int: Kiválasztott nehézség indexe (0..2).

    Vezérlés:
        FEL/LE: navigáció
        ENTER: kiválasztás
        ESC vagy ablak bezárás: kilépés az alkalmazásból
    """
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


def main() -> None:
    """Belépési pont. Pygame inicializálása, főmenü és játék indítása.

    Paraméterek:
        Nincs.

    Visszatérés:
        None

    Kivétel dobása:
        pygame.error: Ha az ablak létrehozása hibát ad.
    """
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    while True:
        difficulty_index = menu_loop(screen, clock)
        game_loop(screen, clock, difficulty_index)


if __name__ == "__main__":
    main()
