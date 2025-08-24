# HÁZI FELADAT – Hibrid logika
#
# Ha abs(dx) > 120 , kényszeríts oldalirányú mozgást (balra/jobbra), ne lőj.
# Ha abs(dx) <= 20 , elsőbbség a lövésé.
# Mérd össze a pontszámot: hibrid vs tiszta ML módban (3–3 perc).

import sys
from typing import Tuple, List, Dict, Any, Optional
import pygame
from helper import *
import joblib

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
    """ML-alapú + hibrid döntés generálása az AI számára.

    Prioritások:
        1) Ha van 'star' power-up, vízszintben rááll és – ha középre ér – lő.
        2) Ha nincs power-up, a legközelebbi ellenséget célozza:
           - Ha abs(dx) > FAR_X: csak bal/jobb mozgás (nem lő).
           - Ha abs(dx) > ALIGN_EPS: közelítsen balra/jobbra (nem lő).
           - Ha abs(dx) <= ALIGN_EPS: ha letelt a késleltetés -> lő.
        3) Ha nincs ellenfél vagy modellhiba van, None-t ad vissza, hogy a
           szabály-alapú logika vegye át a döntést.

    Paraméterek:
        player_rect (pygame.Rect): A játékos ütköződoboza.
        enemies (List[Dict[str,Any]]): Ellenségek listája („rect”, „image” kulcsokkal).
        powerups (pygame.sprite.Group): Aktív power-up objektumok (pl. 'star').
        shoot_delay (int): Lövési késleltetés ms-ban (power-upokkal korrigálva).
        last_shot_time (int): Az utolsó lövés ideje `pygame.time.get_ticks()`-ben.

    Visszatérés:
        Optional[Dict[str,Any]]: Akciószótár {"move": Optional[str], "shoot": bool}
        vagy None (ha nincs ellenfél / nem tud dönteni).

    Kivétel dobása:
        Nincs (predikciós hibákat belül elnyeljük).
    """
    # 1) STAR PRIORITY – először a csillag
    stars = [p for p in powerups if getattr(p, "type", None) == "star"]
    if stars:
        star = min(stars, key=lambda p: abs(p.rect.centerx - player_rect.centerx))
        dx_star = star.rect.centerx - player_rect.centerx
        # a csillaghoz szűkebb epsilon is elég
        align_eps_star = ALIGN_EPS_BASE
        action = {"move": None, "shoot": False}
        if dx_star < -5:
            action["move"] = "left"
        elif dx_star > 5:
            action["move"] = "right"
        if abs(dx_star) <= align_eps_star and pygame.time.get_ticks() - last_shot_time > shoot_delay:
            action["shoot"] = True
        return action

    # 2) Nincs ellenfél -> átadjuk a döntést a szabály-alapúnak
    if not enemies:
        return None

    # Legközelebbi ellenfél (euklideszi)
    target = min(
        enemies,
        key=lambda e: ((e["rect"].centerx - player_rect.centerx) ** 2 +
                       (e["rect"].centery - player_rect.centery) ** 2)
    )
    dx = target["rect"].centerx - player_rect.centerx
    # Dinamikus „találati folyosó”: kicsi sprite-oknál nagyobb relatív slack
    align_eps = max(ALIGN_EPS_BASE, target["rect"].width // 3)

    action = {"move": None, "shoot": False}

    # 3) Hibrid célzás: először igazodás vízszintben, csak aztán lövés
    if abs(dx) > FAR_X:
        action["move"] = "left" if dx < 0 else "right"
        return action

    if abs(dx) > align_eps:
        action["move"] = "left" if dx < 0 else "right"
        return action

    # Itt már nagyjából középen vagyunk -> lövés, ha letelt a késleltetés
    if pygame.time.get_ticks() - last_shot_time > shoot_delay:
        action["shoot"] = True
        return action

    # Ha épp nem lőhetünk, maradunk (nem rángatjuk feleslegesen)
    return action



def draw_ui(screen: pygame.Surface,
            level: int,
            lives: int,
            heart_img: pygame.Surface,
            score: int,
            ai_mode: bool) -> None:
    """Kirajzolja a felhasználói felületet (UI).

    Paraméterek:
        screen (pygame.Surface): Célfelület, ahova rajzolunk.
        level (int): Aktuális szint száma.
        lives (int): Játékos hátralévő életeinek száma.
        heart_img (pygame.Surface): Élet ikon (kb. 32×32 px).
        score (int): Aktuális pontszám.
        ai_mode (bool): True esetén „AI Mód”, különben „Játékos Mód”.

    Visszatérés:
        None

    Kivétel dobása:
        Nincs.
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
    """Kirajzolja a teljes jelenetet (háttér, lövedékek, ellenségek, power-upok, játékos, UI).

    Paraméterek:
        screen (pygame.Surface): Célfelület.
        player_img (pygame.Surface): Játékos sprite.
        player_rect (pygame.Rect): Játékos helyzete.
        enemies (List[Dict[str,Any]]): Ellenségek állapota („image”, „rect” kulcsok kötelezők).
        bullets (List[List[int]]): Lövedékek [x, y] listája.
        powerups (pygame.sprite.Group): Aktív power-up sprite-ok.
        level (int): Szint száma.
        lives (int): Életek száma.
        heart_img (pygame.Surface): Élet ikon.
        score (int): Pontszám.
        ai_mode (bool): AI mód kijelzéséhez.

    Visszatérés:
        None

    Kivétel dobása:
        Nincs.
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

    Kivétel dobása:
        Nincs.
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


def game_loop(screen: pygame.Surface,
              clock: pygame.time.Clock,
              difficulty_index: int) -> None:
    """Fő játékkör (game loop): eseménykezelés, AI/manuális vezérlés, frissítés, kirajzolás.

    Paraméterek:
        screen (pygame.Surface): Az alkalmazás fő kirajzolási felülete.
        clock (pygame.time.Clock): FPS vezérléséhez szükséges óra.
        difficulty_index (int): Választott nehézség indexe (0..2).

    Visszatérés:
        None

    Kivétel dobása:
        Nincs. Kilépéskor a függvény visszatér a hívóhoz.
    """
    (player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img,
     powerups, player_powerups, score, lives) = initialize_game(difficulty_index)

    # --- mérőblokk inicializálása ---
    use_hybrid = True                 # induljon hibridben
    mode_timer_start = pygame.time.get_ticks()
    scores = {"hybrid": None, "ml": None}

    ai_mode = False
    m_key_pressed = False

    def _mode_key() -> str:
        return "hybrid" if use_hybrid else "ml"

    while True:
        # --- eseménykezelés ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            elif event.type == pygame.KEYDOWN and ai_mode is False:
                # billentyűnaplózás tanításhoz
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

        # --- AI mód váltás (kézzel) ---
        keys = pygame.key.get_pressed()
        if keys[pygame.K_m] and not m_key_pressed:
            ai_mode = not ai_mode
            m_key_pressed = True
            mode_timer_start = pygame.time.get_ticks()  # mérőóra nullázása
            print(f"AI mode toggled: {ai_mode} | mód: {_mode_key()}")
        elif not keys[pygame.K_m]:
            m_key_pressed = False

        # --- AI vezérlés vagy manuális ---
        if ai_mode:
            shoot_delay = update_shoot_delay(player_powerups)
            ext_action = decide_action_ml(
                player_rect, enemies, powerups,
                shoot_delay,
                level_data["last_shot_time"]
            )
            if ext_action is None:
                # fallback a szabály-alapú logikára (helper.decide_action)
                ext_action = decide_action(player_rect, enemies, powerups)

            prev_lives = lives
            lives, game_over, score = update_game_state(
                None, player_rect, bullets, enemies, all_positions,
                level_data, lives, score, powerups, player_powerups,
                ai_mode=True, external_ai_action=ext_action
            )

            # Sorátlépés (enemy breach) külön ellenőrzése – ha még nem vettünk el életet
            if not game_over and lives == prev_lives and enemy_breached_player_row(player_rect, enemies):
                lives -= 1
                if lives <= 0:
                    # 3 perc előtt vége -> aktuális mód eredményének eltárolása és kiírása
                    scores[_mode_key()] = score
                    print("Végső eredmények (idő előtt):", scores)
                    draw_game_over(screen); pygame.time.wait(3000); return
                reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)

            # --- 3 perces automatikus módváltás + teljes újrakezdés ---
            elapsed = (pygame.time.get_ticks() - mode_timer_start) / 1000
            if elapsed >= 180:
                # elért pont mentése az aktuális módhoz
                scores[_mode_key()] = score
                print("Eddigi eredmények:", scores)

                # következő módra váltunk (hibrid <-> tiszta ML) ÉS teljes reset a játék elejére
                use_hybrid = not use_hybrid
                mode_timer_start = pygame.time.get_ticks()
                (player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img,
                 powerups, player_powerups, score, lives) = initialize_game(difficulty_index)
                print(f"[Mérés] Új szakasz indul: mód = {_mode_key()} (játék teljesen újraindítva)")

        else:
            # kézi irányítás
            prev_lives = lives
            lives, game_over, score = update_game_state(
                keys, player_rect, bullets, enemies, all_positions,
                level_data, lives, score, powerups, player_powerups, ai_mode=False
            )
            # Manuális módban is őrizzük meg a klasszikus „sorátlépés” szabályt
            if not game_over and lives == prev_lives and enemy_breached_player_row(player_rect, enemies):
                lives -= 1
                if lives <= 0:
                    draw_game_over(screen); pygame.time.wait(3000); return
                reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)

        # --- Game Over kezelése (általános) ---
        if lives <= 0:
            if ai_mode:
                # 3 perc előtt is rögzítjük az aktuális mód eredményét
                scores[_mode_key()] = score
                print("Végső eredmények:", scores)
            draw_game_over(screen)
            pygame.time.wait(3000)
            return

        # --- Kirajzolás ---
        draw_game(screen, player_img, player_rect, enemies, bullets, powerups,
                  level_data["level"], lives, heart_img, score, ai_mode)
        clock.tick(60)


def menu_loop(screen: pygame.Surface, clock: pygame.time.Clock) -> int:
    """Főmenü ciklus: elemválasztás és nehézség állítása.

    Paraméterek:
        screen (pygame.Surface): Kijelző felülete.
        clock (pygame.time.Clock): FPS kontroll.

    Visszatérés:
        int: Kiválasztott nehézség indexe (0..2).

    Kivétel dobása:
        Nincs. Ablak bezárásakor a program kiléphet.
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
    """Belépési pont: Pygame inicializálása, főmenü és játék indítása.

    Paraméterek:
        Nincs.

    Visszatérés:
        None

    Kivétel dobása:
        Nincs. A függvény a program fő ciklusát futtatja, amíg a felhasználó ki nem lép.
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
