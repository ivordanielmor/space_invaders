import sys
from typing import Tuple, List, Dict, Any, Optional
import pygame
from helper import *
import joblib
from csv_helper import init_csv

# --- ML modell betöltése (globálisan egyszer) ---
try:
    model = joblib.load("player_model.joblib")
    model_loaded = True
    print("ML modell sikeresen betöltve.")
except Exception as e:
    print("Figyelem: modell betöltése sikertelen:", e)
    model = None
    model_loaded = False

# --- Hibrid célzási küszöbök ---
ALIGN_EPS = 15      # ennyin belül „pont középen vagyunk” -> lőhetünk
FAR_X = 120         # ezen túl csak vízszint mozgás, nem lövünk
ALIGN_EPS_BASE = 12  # minimális „találati folyosó” fél-szélesség px-ben

def decide_action_ml(player_rect: pygame.Rect,
                     enemies: List[Dict[str, Any]],
                     powerups: pygame.sprite.Group,
                     shoot_delay: int,
                     last_shot_time: int) -> Optional[Dict[str, Any]]:
    """ML-alapú + hibrid döntés generálása az AI számára."""
    stars = [p for p in powerups if getattr(p, "type", None) == "star"]
    if stars:
        star = min(stars, key=lambda p: abs(p.rect.centerx - player_rect.centerx))
        dx_star = star.rect.centerx - player_rect.centerx
        align_eps_star = ALIGN_EPS_BASE
        action = {"move": None, "shoot": False}
        if dx_star < -5:
            action["move"] = "left"
        elif dx_star > 5:
            action["move"] = "right"
        if abs(dx_star) <= align_eps_star and pygame.time.get_ticks() - last_shot_time > shoot_delay:
            action["shoot"] = True
        return action
    if not enemies:
        return None
    target = min(enemies, key=lambda e: ((e["rect"].centerx - player_rect.centerx) ** 2 +
                                        (e["rect"].centery - player_rect.centery) ** 2))
    dx = target["rect"].centerx - player_rect.centerx
    align_eps = max(ALIGN_EPS_BASE, target["rect"].width // 3)
    action = {"move": None, "shoot": False}
    if abs(dx) > FAR_X:
        action["move"] = "left" if dx < 0 else "right"
        return action
    if abs(dx) > align_eps:
        action["move"] = "left" if dx < 0 else "right"
        return action
    if pygame.time.get_ticks() - last_shot_time > shoot_delay:
        action["shoot"] = True
        return action
    return action

def draw_ui(screen: pygame.Surface,
            level: int,
            lives: int,
            heart_img: pygame.Surface,
            score: int,
            ai_mode: bool) -> None:
    """Kirajzolja a felhasználói felületet (UI)."""
    font = pygame.font.SysFont(None, 36)
    screen.blit(font.render(f"Level {level}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (WIDTH - 150, 10))
    mode_text = "AI Mód" if ai_mode else "Játékos Mód"
    mode_color = (0, 255, 0) if ai_mode else (255, 255, 0)
    mode_surface = font.render(f"{mode_text} (M = váltás)", True, mode_color)
    screen.blit(mode_surface, (10, HEIGHT - 40))
    for i in range(lives):
        screen.blit(heart_img, (10 + i * 34, 50))

def draw_game(screen: pygame.Surface,
              player_img: pygame.Surface,
              player_rect: pygame.Rect,
              enemies: List[Dict[str, Any]],
              bullets: List[List[int]],
              powerups: pygame.sprite.Group,
              level: int,
              lives: int,
              heart_img: pygame.Surface,
              score: int,
              ai_mode: bool) -> None:
    """Kirajzolja a teljes jelenetet."""
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
    """Kirajzolja a „GAME OVER” képernyőt."""
    screen.fill((0, 0, 0))
    font = pygame.font.SysFont(None, 72)
    text = font.render("GAME OVER", True, (255, 0, 0))
    screen.blit(text, ((WIDTH - text.get_width()) // 2, HEIGHT // 2 - 40))
    font_small = pygame.font.SysFont(None, 36)
    try:
        with open("scoreboard.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            scores = sorted([(row[0], int(row[1])) for row in reader], key=lambda x: x[1], reverse=True)[:5]
            for i, (player, score) in enumerate(scores):
                score_text = font_small.render(f"{player}: {score}", True, (255, 255, 255))
                screen.blit(score_text, ((WIDTH - score_text.get_width()) // 2, HEIGHT // 2 + 20 + i * 40))
    except Exception as e:
        print(f"Hiba a pontszámok olvasásakor: {e}")
    pygame.display.flip()

def initialize_game(difficulty_index: int
                    ) -> Tuple[pygame.Surface, pygame.Rect, List[Dict[str, Any]],
                               List[List[int]], List[Tuple[int, int]], Dict[str, Any],
                               pygame.Surface, pygame.sprite.Group, Dict[str, int],
                               int, int]:
    """Inicializálja a játék állapotát."""
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

def menu_loop(screen: pygame.Surface, clock: pygame.time.Clock) -> Tuple[int, str]:
    """Főmenü ciklus: elemválasztás, nehézség állítása és játékosnév bevitel."""
    font = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 28)
    options = ["Indítás", "Nehézség: Normál", "Játékosnév: Player", "Kilépés"]
    selected = 0
    difficulties = ["Könnyű", "Normál", "Nehéz"]
    difficulty_index = 1
    player_name = "Player"
    input_active = False
    cursor_visible = True
    cursor_timer = 0
    max_name_length = 20

    while True:
        screen.fill((0, 0, 0))
        # Frissítjük a kurzort villogáshoz (500 ms-onként vált)
        current_time = pygame.time.get_ticks()
        if current_time - cursor_timer > 500:
            cursor_visible = not cursor_visible
            cursor_timer = current_time

        for i, text in enumerate(options):
            # Kiemelés a kiválasztott opcióhoz
            color = (255, 255, 0) if i == selected else (255, 255, 255)
            if i == 2 and input_active:
                # Játékosnév bevitel közben: zöld szín és villogó kurzor
                text = f"Játékosnév: {player_name}{'|' if cursor_visible else ''}"
                color = (0, 255, 0)
            label = font.render(text, True, color)
            screen.blit(label, ((WIDTH - label.get_width()) // 2, 200 + i * 60))

        # Utasítás a bevitelhez
        if selected == 2:
            instruction = font_small.render(
                "Írd be a nevet, majd nyomj Entert (Backspace: törlés, Esc: kilép)",
                True, (200, 200, 200)
            )
            screen.blit(instruction, ((WIDTH - instruction.get_width()) // 2, 400))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    input_active = False  # Kilépés a bevitelből, ha másik opcióra lép
                    options[2] = f"Játékosnév: {player_name or 'Player'}"
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                    input_active = False  # Kilépés a bevitelből
                    options[2] = f"Játékosnév: {player_name or 'Player'}"
                elif event.key == pygame.K_RETURN:
                    if selected == 0:
                        return difficulty_index, player_name or "Player"
                    elif selected == 1:
                        difficulty_index = (difficulty_index + 1) % len(difficulties)
                        options[1] = f"Nehézség: {difficulties[difficulty_index]}"
                    elif selected == 2:
                        input_active = True
                        cursor_visible = True
                        cursor_timer = current_time
                    elif selected == 3:
                        pygame.quit(); sys.exit()
                elif event.key == pygame.K_ESCAPE:
                    if input_active:
                        input_active = False
                        options[2] = f"Játékosnév: {player_name or 'Player'}"
                    else:
                        pygame.quit(); sys.exit()
                elif input_active and selected == 2:
                    if event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                        options[2] = f"Játékosnév: {player_name or 'Player'}"
                    elif event.key == pygame.K_RETURN:
                        input_active = False
                        options[2] = f"Játékosnév: {player_name or 'Player'}"
                    elif event.unicode.isprintable() and len(player_name) < max_name_length:
                        player_name += event.unicode
                        options[2] = f"Játékosnév: {player_name or 'Player'}"

        clock.tick(60)

def game_loop(screen: pygame.Surface,
              clock: pygame.time.Clock,
              difficulty_index: int,
              player_name: str) -> None:
    """Fő játékkör."""
    (player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img,
     powerups, player_powerups, score, lives) = initialize_game(difficulty_index)
    use_hybrid = True
    mode_timer_start = pygame.time.get_ticks()
    scores = {"hybrid": None, "ml": None}
    ai_mode = False
    m_key_pressed = False

    def _mode_key() -> str:
        return "hybrid" if use_hybrid else "ml"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            elif event.type == pygame.KEYDOWN and ai_mode is False:
                debug_print(f"Key pressed: {event.key}, enemies count: {len(enemies)}")
                center = closest_enemy_center(player_rect, enemies)
                debug_print(f"Closest enemy center: {center}")
                if center is not None:
                    cx, cy = center
                    dx = cx - player_rect.centerx
                    dy = cy - player_rect.centery
                    speed_multiplier = level_data["speed_multiplier"]
                    enemy_count = len(enemies)
                    if event.key == pygame.K_LEFT:
                        debug_print("Logging LEFT action")
                        log_example(dx, dy, 0, speed_multiplier, enemy_count)
                    elif event.key == pygame.K_RIGHT:
                        debug_print("Logging RIGHT action")
                        log_example(dx, dy, 1, speed_multiplier, enemy_count)
                    elif event.key == pygame.K_SPACE:
                        debug_print("Logging SPACE action")
                        log_example(dx, dy, 2, speed_multiplier, enemy_count)
                else:
                    debug_print("No enemies, skipping log_example")

        keys = pygame.key.get_pressed()
        if keys[pygame.K_m] and not m_key_pressed:
            ai_mode = not ai_mode
            m_key_pressed = True
            mode_timer_start = pygame.time.get_ticks()
            print(f"AI mode toggled: {ai_mode} | mód: {_mode_key()}")
        elif not keys[pygame.K_m]:
            m_key_pressed = False

        if ai_mode:
            shoot_delay = update_shoot_delay(player_powerups)
            ext_action = decide_action_ml(
                player_rect, enemies, powerups,
                shoot_delay,
                level_data["last_shot_time"]
            )
            if ext_action is None:
                ext_action = decide_action(player_rect, enemies, powerups)
            prev_lives = lives
            lives, game_over, score = update_game_state(
                None, player_rect, bullets, enemies, all_positions,
                level_data, lives, score, powerups, player_powerups,
                ai_mode=True, external_ai_action=ext_action,
                player=player_name
            )
            if not game_over and lives == prev_lives and enemy_breached_player_row(player_rect, enemies):
                lives -= 1
                if lives <= 0:
                    scores[_mode_key()] = score
                    print("Végső eredmények (idő előtt):", scores)
                    draw_game_over(screen); pygame.time.wait(3000); return
                reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
            elapsed = (pygame.time.get_ticks() - mode_timer_start) / 1000
            if elapsed >= 180:
                scores[_mode_key()] = score
                print("Eddigi eredmények:", scores)
                use_hybrid = not use_hybrid
                mode_timer_start = pygame.time.get_ticks()
                (player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img,
                 powerups, player_powerups, score, lives) = initialize_game(difficulty_index)
                print(f"[Mérés] Új szakasz indul: mód = {_mode_key()} (játék teljesen újraindítva)")
        else:
            prev_lives = lives
            lives, game_over, score = update_game_state(
                keys, player_rect, bullets, enemies, all_positions,
                level_data, lives, score, powerups, player_powerups, ai_mode=False,
                player=player_name
            )
            if not game_over and lives == prev_lives and enemy_breached_player_row(player_rect, enemies):
                lives -= 1
                if lives <= 0:
                    draw_game_over(screen); pygame.time.wait(3000); return
                reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)

        if lives <= 0:
            if ai_mode:
                scores[_mode_key()] = score
                print("Végső eredmények:", scores)
            # ÚJ: Mentsd el a végső pontszámot
            save_score(player_name, score)
            draw_game_over(screen)
            pygame.time.wait(3000)
            return

        draw_game(screen, player_img, player_rect, enemies, bullets, powerups,
                  level_data["level"], lives, heart_img, score, ai_mode)
        clock.tick(60)

def main() -> None:
    """Belépési pont."""
    pygame.init()
    init_csv()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()
    while True:
        difficulty_index, player_name = menu_loop(screen, clock)
        game_loop(screen, clock, difficulty_index, player_name)

if __name__ == "__main__":
    main()
