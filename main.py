import sys
from typing import Tuple, List, Dict, Any, Optional
import pygame
from helper import *
import joblib
from csv_helper import init_csv
import csv  # szükséges a draw_game_over-ban használt csv.reader-hez

# --- ML modell betöltése (globálisan egyszer) ---
try:
    model = joblib.load("player_model.joblib")
    model_loaded = True
    print("ML modell sikeresen betöltve.")
except Exception as e:
    # Hibakezelés: ha a modell betöltése sikertelen, a program tovább tud futni
    # (fallback: model = None, és model_loaded = False).
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

    Paraméterek:
        player_rect (pygame.Rect): A játékos aktuális ütközőkerete (pozíció + méret).
        enemies (List[Dict[str, Any]]): Lista ellenségekről, ahol minden elem egy dict, amely
                                        legalább egy "rect" (pygame.Rect) mezőt tartalmaz.
        powerups (pygame.sprite.Group): A jelenet power-up sprite-csoportja.
        shoot_delay (int): A kötelező késleltetés milliszekundumban két lövés között.
        last_shot_time (int): Az utolsó lövés időbélyege (pygame.time.get_ticks() skáláján).

    Visszatérés:
        Optional[Dict[str, Any]]: Akció-dikt, amely a következő kulcsokat tartalmazza:
            - "move": None | "left" | "right"
            - "shoot": bool
        Visszaad None-t, ha nincs cél (például nincs ellenség és nincs releváns powerup).

    Mellékhatás:
        - Prioritást ad a 'star' típusú powerupoknak: ha van közelben, arra pozícionál és lő.
        - Ha nincs star és nincs ellenség, None-t ad vissza.
        - Ha van ellenség, kiválaszt egy targetet (legközelebbi euklideszi távolság szerint),
          majd hibrid szabályok alapján dönt a mozgatásról és lövésről.
        - A függvény nem használ közvetlenül ML-predikciót; a név arra utal, hogy
          itt integrálható egy betanított modell (globális `model`) kiegészítésként.
        - Nem módosít globális állapotot.

    Példa:
        action = decide_action_ml(player_rect, enemies, powerups, 500, last_shot)
    """
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
    """Kirajzolja a felhasználói felületet (UI).

    Paraméterek:
        screen (pygame.Surface): A fő render célfelület.
        level (int): Aktuális játékszint száma.
        lives (int): Megjelenítendő életek száma.
        heart_img (pygame.Surface): Az élet ikon Surface objektuma (32×32 várható).
        score (int): Jelenlegi pontszám.
        ai_mode (bool): Ha True, AI módot jelöl (zöld szöveg), különben sárga.

    Visszatérés:
        None

    Mellékhatás:
        - Kirajzolja a Level, Score és a mód státuszát, valamint az élet ikonokat.
        - Feltételezi, hogy a pygame.font modul inicializálva van.
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
    """Kirajzolja a teljes jelenetet.

    Paraméterek:
        screen (pygame.Surface): Render cél.
        player_img (pygame.Surface): Játékos sprite.
        player_rect (pygame.Rect): Játékos pozícióját tartalmazó Rect.
        enemies (List[Dict[str, Any]]): Ellenségek listája (minden elem dict, legalább "image" és "rect").
        bullets (List[List[int]]): Lövedékek pozíciói (például [x, y]).
        powerups (pygame.sprite.Group): Power-up sprite-ok csoportja.
        level (int): Aktuális szint.
        lives (int): Életek száma.
        heart_img (pygame.Surface): Élet ikon Surface.
        score (int): Pontszám.
        ai_mode (bool): AI mód jelzés.

    Visszatérés:
        None

    Mellékhatás:
        - Kitörli a képernyőt, kirajzolja a lövedékeket, ellenségeket, powerupokat és a játékost,
          majd meghívja a draw_ui-t és frissíti a kijelzőt (`pygame.display.flip()`).
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
    """Kirajzolja a „GAME OVER” képernyőt.

    Paraméterek:
        screen (pygame.Surface): A render cél.

    Visszatérés:
        None

    Mellékhatás:
        - Megjelenít egy nagy "GAME OVER" feliratot.
        - Megpróbálja beolvasni a "scoreboard.csv"-t és megjeleníteni a top 5 pontot.
        - Hibák esetén (fájl hiánya, parse hiba) a kivételt a konzolra írja.
    """
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
    """Inicializálja a játék állapotát.

    Paraméterek:
        difficulty_index (int): 0 = Könnyű, 1 = Normál, 2 = Nehéz.

    Visszatérés:
        Tuple: Rendezett visszatérési érték a következő elemekkel:
            (player_img, player_rect, enemies, bullets, all_positions,
             level_data, heart_img, powerups, player_powerups, score, lives)

    Mellékhatás:
        - Betölti a szükséges sprite-okat (player, enemy, heart).
        - Létrehozza az ellenségek pozícióit és inicializálja az `enemies` listát a
          create_enemies hívásával.
        - Beállítja a lives, enemy_count és speed_multiplier értékeket a nehézség alapján.
        - Inicializálja az üres lövedék-, powerup- és player_powerups-szerkezeteket.
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

def menu_loop(screen: pygame.Surface, clock: pygame.time.Clock) -> Tuple[int, str]:
    """Főmenü: indítás, ranglista, nehézség, játékosnév, kilépés.

    Új: 'Ranglista' opció — Enter vagy Space megnyomására belép a Ranglista-nézetbe.
    A Ranglista-nézetből ESC-sel lehet visszalépni a főmenübe.
    """
    font = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 28)
    difficulties = ["Könnyű", "Normál", "Nehéz"]
    difficulty_index = 1
    player_name = "Player"

    options = [
        "Indítás",
        "Ranglista",
        f"Nehézség: {difficulties[difficulty_index]}",
        f"Játékosnév: {player_name}",
        "Kilépés"
    ]
    selected = 0
    input_active = False
    cursor_visible = True
    cursor_timer = 0
    max_name_length = 20

    def draw_menu() -> None:
        """Belső függvény: a főmenü kirajzolása (lokális, nincs docstring a felső szinten)."""
        screen.fill((0, 0, 0))
        for i, text in enumerate(options):
            color = (255, 255, 0) if i == selected else (255, 255, 255)
            # ha a játékosnév mező aktív, zöld és kurzor villog
            if i == 3 and input_active:
                display = f"Játékosnév: {player_name}{'|' if cursor_visible else ''}"
                color = (0, 255, 0)
            else:
                display = text
            label = font.render(display, True, color)
            screen.blit(label, ((WIDTH - label.get_width()) // 2, 200 + i * 60))

        if selected == 3:
            instruction = font_small.render(
                "Írd be a nevet, majd nyomj Entert (Backspace: törlés, Esc: kilép)",
                True, (200, 200, 200)
            )
            screen.blit(instruction, ((WIDTH - instruction.get_width()) // 2, 400))

        pygame.display.flip()

    # Pygame-alapú TOP5 rajzoló (lokális függvény, elkerüli a ciklikus importot)
    def draw_top5_screen() -> None:
        from csv_helper import load_top5  # lokális import a ciklikus import elkerüléséhez
        screen.fill((0, 0, 0))
        title = font.render("Ranglista - TOP 5", True, (255, 255, 255))
        screen.blit(title, ((WIDTH - title.get_width()) // 2, 80))

        top = load_top5()
        if not top:
            msg = font_small.render("Még nincs adat a ranglistán.", True, (200, 200, 200))
            screen.blit(msg, ((WIDTH - msg.get_width()) // 2, HEIGHT // 2))
        else:
            for i, (name, score) in enumerate(top, start=1):
                line = font_small.render(f"{i}. {name} — {score} pont", True, (255, 255, 255))
                screen.blit(line, ((WIDTH - line.get_width()) // 2, 160 + i * 40))

        hint = font_small.render("Esc = vissza a főmenübe", True, (180, 180, 180))
        screen.blit(hint, ((WIDTH - hint.get_width()) // 2, HEIGHT - 60))
        pygame.display.flip()

    while True:
        # kurzor villogása
        current_time = pygame.time.get_ticks()
        if current_time - cursor_timer > 500:
            cursor_visible = not cursor_visible  # nonlocal emuláció - felülíródik lent újra
            cursor_timer = current_time

        # Rajzolás
        draw_menu()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.KEYDOWN:
                # navigáció
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    input_active = False
                    options[3] = f"Játékosnév: {player_name or 'Player'}"
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                    input_active = False
                    options[3] = f"Játékosnév: {player_name or 'Player'}"

                # kiválasztás (Enter vagy Space)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected == 0:  # Indítás
                        return difficulty_index, player_name or "Player"

                    elif selected == 1:  # Ranglista — belépünk a ranglista nézetbe
                        in_scoreboard = True
                        while in_scoreboard:
                            draw_top5_screen()
                            for ev in pygame.event.get():
                                if ev.type == pygame.QUIT:
                                    pygame.quit(); sys.exit()
                                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                                    in_scoreboard = False
                            clock.tick(30)
                        # visszatérés után a menü újrarajzolódik
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                        cursor_visible = True
                        cursor_timer = pygame.time.get_ticks()

                    elif selected == 2:  # Nehézség váltás
                        difficulty_index = (difficulty_index + 1) % len(difficulties)
                        options[2] = f"Nehézség: {difficulties[difficulty_index]}"

                    elif selected == 3:  # Játékosnév bevitel indítása
                        input_active = True
                        cursor_visible = True
                        cursor_timer = current_time

                    elif selected == 4:  # Kilépés
                        pygame.quit(); sys.exit()

                elif event.key == pygame.K_ESCAPE:
                    if input_active:
                        input_active = False
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                    else:
                        pygame.quit(); sys.exit()

                # név bevitel kezelése, ha aktív
                elif input_active and selected == 3:
                    if event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                    elif event.key == pygame.K_RETURN:
                        input_active = False
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                    else:
                        # unicode karakter hozzáadása, ha megengedett
                        if getattr(event, "unicode", "") and event.unicode.isprintable() and len(player_name) < max_name_length:
                            player_name += event.unicode
                            options[3] = f"Játékosnév: {player_name or 'Player'}"

        # frissítési tempó
        clock.tick(60)
def game_loop(screen: pygame.Surface,
              clock: pygame.time.Clock,
              difficulty_index: int,
              player_name: str) -> None:
    """Fő játékkör — belső ciklus a játék futtatásához.

    Paraméterek:
        screen (pygame.Surface): A fő render célfelület.
        clock (pygame.time.Clock): Pygame clock objektum a frame-rate korlátozásához.
        difficulty_index (int): Nehézség index (0=Könnyű,1=Normál,2=Nehéz).
        player_name (str): A jelenlegi játékos neve, amely a ranglistába mentéskor használatos.

    Visszatérés:
        None

    Mellékhatás:
        - Inicializálja a játék állapotát az `initialize_game` hívásával.
        - Kezeli a felhasználói inputot (billentyűk, kilépés), az AI váltását (M),
          valamint a manuális játékos-bemenetet (nyíl, space) és azok logolását.
        - Ha AI mód be van kapcsolva, külső döntést szerez `decide_action_ml`-ből
          (visszaesés: `decide_action`), és ennek megfelelően hívja az `update_game_state`-et.
        - Kezeli az életvesztést, a szint-resetet és a mérési időszakok közötti
          átváltást (use_hybrid váltása idő alapján).
        - A játék végén elmenti a pontszámot `save_score`-ral és kirajzolja a TOP5-öt.
        - A függvény váratlan hibákat nem kezeli lokálisan; a hívó felel a kivételekért.

    Példa:
        game_loop(screen, clock, 1, "Alice")
    """
    (player_img, player_rect, enemies, bullets, all_positions, level_data, heart_img,
     powerups, player_powerups, score, lives) = initialize_game(difficulty_index)
    use_hybrid = True
    mode_timer_start = pygame.time.get_ticks()
    scores = {"hybrid": None, "ml": None}
    ai_mode = False
    m_key_pressed = False

    def _mode_key() -> str:
        """Segédfüggvény: visszaadja az aktuális mérési mód kulcsát ('hybrid' vagy 'ml')."""
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
            print_top5()
            draw_game_over(screen)
            pygame.time.wait(3000)
            return

        draw_game(screen, player_img, player_rect, enemies, bullets, powerups,
                  level_data["level"], lives, heart_img, score, ai_mode)
        clock.tick(60)

def main() -> None:
    """Belépési pont — inicializálja a Pygame-et és indítja a menüt/játékhurokot.

    Paraméterek:
        Nincsenek.

    Visszatérés:
        None

    Mellékhatás:
        - Inicializálja a pygame modult és a scoreboard CSV-t (`init_csv`).
        - Létrehozza a képernyőt és a clock-ot, majd belép a menü/játék ciklusba.
        - A program a felhasználó kilépéséig fut; ha a fájl közvetlenül fut, meghívja magát.
    """
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
