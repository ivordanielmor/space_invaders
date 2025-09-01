"""Space Invaders – fő modul.

Feladat:
- Pygame inicializálása, főmenü és játékhurok futtatása.
- Asset-ek és ranglista fájlok központi helyekről való használata:
  - Képek:        assets/images
  - CSV fájlok:   assets/csv
  - Ranglista:    assets/csv/scoreboard.csv
- UI-rajzolás és képek betöltése az ui_helper modulon át történik,
  így itt nem tartunk duplikált draw_* vagy load_* függvényeket.
- Játékmenet logika (pl. update_game_state, decide_action) a helper modulban.

Billentyűk:
- Nyilak: mozgatás kézi módban.
- SPACE: lövés kézi módban.
- M: AI mód váltása.
- ESC: vissza / kilépés kontextustól függően.

ML:
- A `player_model.joblib` betöltése opcionális. Ha nem sikerül, a játék fut
  szabály-alapú döntéssel is (helper.decide_action).

Könyvtárak:
- pygame, joblib
- helyi modulok: helper, ui_helper, csv_helper

Továbbfejlesztési irány: 
- Egyedi USP: tanítható AI – élőben tanítható profilok, módváltás (player/AI/hibrid), látható viselkedéskülönbség.

- Kiforrott core loop: 10 hullám + 1 miniboss + 1 boss, 3 nehézség, tiszta célok és jutalmazás.

- Ellenség-ökoszisztéma: min. 5 eltérő enemy-típus (minták, lövések, mozgások), jól telegráfozott támadások.

- Fegyver/Power-up rendszer: ~6 pickup (rapid, spread, shield, bomb, magnet, slow-mo) + egyszerű run-végi upgrade shop.

- Pontozás/kombó: szorzó, chain, “perfect wave” bónusz; risk-reward (közelebb mész → nagyobb pont).

- Juice & AV: ütős SFX, zene, képernyőrázás, hit-stop, lövedék-trail, robbanás VFX; egységes vizuális stílus.

- UX & QoL: rövid interaktív tutorial, pause menü, beállítások (hangerő, grafika), billentyű/konfigurálható kontroller, színtévesztő mód.

- Teljesítmény és skálázás: stabil 60 FPS, több felbontás/teljes képernyő, alacsony késleltetésű input.

- Online réteg: ranglista (globális/baráti), napi/hetente seedelt kihívás; alap anti-cheat ellenőrzések.

- Kiadás-kész csomag: build pipeline (Win/macOS/Linux), crash-log, opcionális analitika, licencelt/saját assetek, ikonok, rövid trailer + store-oldal.
"""

import sys
from typing import Tuple, List, Dict, Any, Optional
import pygame
import joblib
import config as cfg

# Játékmenet logika és utilok
from helper import (
    decide_action, update_game_state, reset_level, generate_enemy_positions,
    enemy_breached_player_row, closest_enemy_center, log_example,
    update_shoot_delay, debug_print, create_enemies
)

# CSV-műveletek (assets/csv átadható, ha a függvények támogatják)
from csv_helper import init_csv, save_score_if_record, print_top5

# UI és asset-útvonalak
import ui_helper as ui


# --- ML modell betöltése (globálisan egyszer) ---
try:
    model = joblib.load("player_model.joblib")
    model_loaded = True
    print("ML modell sikeresen betöltve.")
except Exception as e:
    # A játék enélkül is fut; a döntés visszaesik szabály-alapúra.
    print("Figyelem: modell betöltése sikertelen:", e)
    model = None
    model_loaded = False


# --- Hibrid célzási küszöbök ---
ALIGN_EPS = 15       # ennyin belül „középen” vagyunk → lőhetünk
FAR_X = 120          # ettől messzebb csak vízszintes igazítás
ALIGN_EPS_BASE = 12  # minimális találati folyosó fél-szélesség px-ben


def decide_action_ml(player_rect: pygame.Rect,
                     enemies: List[Dict[str, Any]],
                     powerups: pygame.sprite.Group,
                     shoot_delay: int,
                     last_shot_time: int) -> Optional[Dict[str, Any]]:
    global model, model_loaded  # a main.py tetején betöltött modell
    """ML-barát hibrid döntés az AI számára.

    Paraméterek:
        player_rect (pygame.Rect): A játékos aktuális pozíciója és mérete.
        enemies (List[Dict[str, Any]]): Ellenségek listája. Minden elem legalább "rect" kulcsot tartalmaz.
        powerups (pygame.sprite.Group): A képernyőn lévő power-up sprite-ok.
        shoot_delay (int): Minimális idő (ms) két lövés között.
        last_shot_time (int): Az utolsó lövés időbélyege (pygame.time.get_ticks skálán).

    Visszatérés:
        Optional[Dict[str, Any]]: Akció-dikt a következő kulcsokkal:
            - "move": None | "left" | "right"
            - "shoot": bool
        None, ha nincs cél (nincs ellenség és releváns powerup sincs).

    Mellékhatás:
        Nincs. Nem módosít globális állapotot, csak számol és visszatér.

    Megjegyzések:
        - Star power-up prioritás: először arra igazít és csak igazítás után lő.
        - Ha van ellenség, kiválasztja a legközelebbit euklideszi távolság alapján,
          majd hibrid szabályokkal dönt:
            * nagyon távol: csak oldalirányú igazítás
            * közeli, de nem illesztett: finom igazítás
            * jól illesztett és letelt a shoot_delay: lövés
        - `model` jelenleg nem kerül meghívásra; ide integrálható ML-predikció.

    Példa:
        action = decide_action_ml(player_rect, enemies, powerups, 500, last_shot)
    """
    # 1) Power-up prioritás
    stars = [p for p in powerups if getattr(p, "type", None) == "star"]
    if stars:
        star = min(stars, key=lambda p: abs(p.rect.centerx - player_rect.centerx))
        dx_star = star.rect.centerx - player_rect.centerx
        action = {"move": None, "shoot": False}
        if dx_star < -5: action["move"] = "left"
        elif dx_star > 5: action["move"] = "right"
        if abs(dx_star) <= ALIGN_EPS_BASE and pygame.time.get_ticks() - last_shot_time > shoot_delay:
            action["shoot"] = True
        return action

    # 2) Nincs cél
    if not enemies:
        return None

    # 3) Cél és metrikák
    target = min(enemies, key=lambda e: ((e["rect"].centerx - player_rect.centerx) ** 2 +
                                         (e["rect"].centery - player_rect.centery) ** 2))
    dx = target["rect"].centerx - player_rect.centerx
    dy = target["rect"].centery - player_rect.centery
    align_eps = max(ALIGN_EPS_BASE, target["rect"].width // 3)
    action = {"move": None, "shoot": False}

    # 4) ML-predikció (0=left, 1=right, 2=shoot)
    used_ml = False
    if model_loaded and model is not None:
        try:
            pred = int(model.predict([[dx, dy]])[0])
            used_ml = True
            if pred == 0:
                action["move"] = "left"
            elif pred == 1:
                action["move"] = "right"
            elif pred == 2:
                action["shoot"] = True
        except Exception:
            used_ml = False

    # 5) Visszaesés szabályokra, ha nincs ML
    if not used_ml:
        if abs(dx) > FAR_X:
            action["move"] = "left" if dx < 0 else "right"
        elif abs(dx) > align_eps:
            action["move"] = "left" if dx < 0 else "right"
        elif pygame.time.get_ticks() - last_shot_time > shoot_delay:
            action["shoot"] = True

    # 6) Védőkorlátok / finomhangolás
    now = pygame.time.get_ticks()
    if action["shoot"]:
        if abs(dx) > align_eps or (now - last_shot_time) <= shoot_delay:
            # még nem jó az igazítás vagy nem telt le a késleltetés → igazítás előbb
            action["shoot"] = False
            if abs(dx) > align_eps:
                action["move"] = "left" if dx < 0 else "right"
    if action["move"] is None and abs(dx) > align_eps:
        action["move"] = "left" if dx < 0 else "right"
    if abs(dx) > FAR_X:
        action["shoot"] = False  # nagyon távol: előbb igazítás

    return action

def initialize_game(difficulty_index: int
                    ) -> Tuple[pygame.Surface, pygame.Rect, List[Dict[str, Any]],
                               List[List[int]], List[Tuple[int, int]], Dict[str, Any],
                               pygame.Surface, pygame.sprite.Group, Dict[str, int],
                               int, int]:
    """Inicializálja a játék kezdő állapotát a választott nehézség szerint.

    Cél:
        Betölti a szükséges sprite-okat, előkészíti az ellenségeket, a lövedéklistát,
        a power-up csoportot és a szint metaadatait. Minden, a játékkörhöz
        szükséges állapotot visszaad egy rendezett tuple-ben.

    Paraméterek:
        difficulty_index (int): A kívánt nehézség. Elfogadott értékek:
            0 = „Könnyű”  → több élet, kevesebb ellenfél, lassabb mozgás
            1 = „Normál”  → alap beállítás
            2 = „Nehéz”   → kevesebb élet, több ellenfél, gyorsabb mozgás
            Ha a bemenet nem {0,1,2}, akkor 1-re (Normál) normalizálódik.

    Visszatérés:
        Tuple[
            pygame.Surface,                 # player_img
            pygame.Rect,                    # player_rect
            List[Dict[str, Any]],           # enemies
            List[List[int]],                # bullets
            List[Tuple[int, int]],          # all_positions
            Dict[str, Any],                 # level_data
            pygame.Surface,                 # heart_img
            pygame.sprite.Group,            # powerups
            Dict[str, int],                 # player_powerups
            int,                            # score
            int                             # lives
        ]

        A tuple elemei részletesen:
            - player_img: A játékos sprite-ja (ui.load_player).
            - player_rect: A játékos kezdő pozíciója. Alap: képernyő alja, közép.
            - enemies: Ellenségek listája. Minden elem kulcsai:
                {"rect": pygame.Rect, "speed": float, "image": pygame.Surface,
                 "float_x": float, "float_y": float}
            - bullets: Üres lista a lövedékek [x, y] koordinátáinak.
            - all_positions: Előre generált rácspozíciók az ellenségeknek (generate_enemy_positions).
            - level_data: Szint metaadatok:
                {
                  "level": int,                 # kezdetben 1
                  "enemy_count": int,           # nehézségtől függ
                  "last_shot_time": int,        # kezdetben 0
                  "dx": float,                  # vízszintes lépés (sebességszorzótól függ)
                  "enemy_img": pygame.Surface,  # alap ellenség sprite
                  "speed_multiplier": float     # nehézséghez tartozó szorzó
                }
            - heart_img: Élet ikon sprite (ui.load_heart).
            - powerups: Üres pygame.sprite.Group a pályán megjelenő power-upokhoz.
            - player_powerups: Üres dict az aktivált power-up időbélyegekhez.
            - score: Kezdő pontszám, 0.
            - lives: Kezdő életek száma a nehézség alapján.

    Mellékhatás:
        - Fájlrendszerből képeket olvas az `assets/images` mappából az ui_helperen át.
        - Ellenségeket hoz létre véletlen mérettel és színnel (nem determinisztikus kezdőállapot).

    Kivétel:
        - pygame.error / FileNotFoundError a sprite-ok betöltésekor (tovább propagálódik).

    Függőségek:
        - ui.load_player, ui.load_enemy, ui.load_heart
        - generate_enemy_positions, create_enemies

    Példa:
        player_img, player_rect, enemies, bullets, all_pos, level_data, heart_img, powerups, player_pw, score, lives = initialize_game(1)
    """
    player_img, player_rect = ui.load_player()
    enemy_img = ui.load_enemy()
    heart_img = ui.load_heart()

    all_positions = generate_enemy_positions()

    # Normalizálás ismeretlen bemenetre
    if difficulty_index not in (0, 1, 2):
        difficulty_index = 1

    if difficulty_index == 0:
        lives, enemy_count, speed_multiplier = 5, 6, 0.8
    elif difficulty_index == 1:
        lives, enemy_count, speed_multiplier = 3, 8, 1.0
    else:
        lives, enemy_count, speed_multiplier = 2, 10, 1.3

    level_data: Dict[str, Any] = {
        "level": 1,
        "enemy_count": enemy_count,
        "last_shot_time": 0,
        "dx": 2 * speed_multiplier,
        "enemy_img": enemy_img,
        "speed_multiplier": speed_multiplier,
    }

    enemies = create_enemies(enemy_img, all_positions.copy(), enemy_count, speed_multiplier)

    bullets: List[List[int]] = []
    powerups = pygame.sprite.Group()
    player_powerups: Dict[str, int] = {}
    score = 0

    return (player_img, player_rect, enemies, bullets, all_positions,
            level_data, heart_img, powerups, player_powerups, score, lives)


def menu_loop(screen: pygame.Surface, clock: pygame.time.Clock) -> Tuple[int, str]:
    """Főmenü hurok. Kezeli a választást, ranglista nézetet és névbevitelt.

    Paraméterek:
        screen (pygame.Surface): Célfelület a rajzoláshoz.
        clock (pygame.time.Clock): FPS szabályozás.

    Visszatérés:
        Tuple[int, str]: (difficulty_index, player_name)

    Mellékhatás:
        - Képernyőre rajzol.
        - Eseményeket fogyaszt a Pygame event queue-ból.
        - Beléphet a ranglista nézetbe (ui.draw_top5).

    Billentyűk:
        Fel/Le: menüelem választás.
        Enter/Space: kiválasztás.
        ESC: kilépés.
        Név mező aktív: karakterbevitel, Backspace töröl.

    Példa:
        diff, name = menu_loop(screen, clock)
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
        """A főmenü kirajzolása a `screen`-re."""
        screen.fill((0, 0, 0))
        for i, text in enumerate(options):
            color = (255, 255, 0) if i == selected else (255, 255, 255)
            if i == 3 and input_active:
                display = f"Játékosnév: {player_name}{'|' if cursor_visible else ''}"
                color = (0, 255, 0)
            else:
                display = text
            label = font.render(display, True, color)
            screen.blit(label, ((cfg.WIDTH - label.get_width()) // 2, 200 + i * 60))

        if selected == 3:
            instruction = font_small.render(
                "Írd be a nevet, majd Enter (Backspace: törlés, Esc: kilép)",
                True, (200, 200, 200)
            )
            screen.blit(instruction, ((cfg.WIDTH - instruction.get_width()) // 2, 400))

        pygame.display.flip()

    def draw_top5_screen() -> None:
        """Ranglista nézet rajzolása (TOP5) és visszalépés ESC-re."""
        ui.draw_top5(screen, font, font_small)

    while True:
        # kurzor villogása
        current_time = pygame.time.get_ticks()
        if current_time - cursor_timer > 500:
            cursor_visible = not cursor_visible
            cursor_timer = current_time

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

                # kiválasztás
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected == 0:  # Indítás
                        return difficulty_index, player_name or "Player"

                    elif selected == 1:  # Ranglista
                        in_scoreboard = True
                        while in_scoreboard:
                            draw_top5_screen()
                            for ev in pygame.event.get():
                                if ev.type == pygame.QUIT:
                                    pygame.quit(); sys.exit()
                                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                                    in_scoreboard = False
                            clock.tick(30)
                        # visszatérés után
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                        cursor_visible = True
                        cursor_timer = pygame.time.get_ticks()

                    elif selected == 2:  # Nehézség
                        difficulty_index = (difficulty_index + 1) % len(difficulties)
                        options[2] = f"Nehézség: {difficulties[difficulty_index]}"

                    elif selected == 3:  # Név bevitel
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

                # név bevitel
                elif input_active and selected == 3:
                    if event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                    elif event.key == pygame.K_RETURN:
                        input_active = False
                        options[3] = f"Játékosnév: {player_name or 'Player'}"
                    else:
                        if getattr(event, "unicode", "") and event.unicode.isprintable() and len(player_name) < max_name_length:
                            player_name += event.unicode
                            options[3] = f"Játékosnév: {player_name or 'Player'}"

        clock.tick(60)


def game_loop(screen: pygame.Surface,
              clock: pygame.time.Clock,
              difficulty_index: int,
              player_name: str) -> None:
    """Fő játékhurok. Kezeli a kézi és AI módot, életciklus eseményeket, pontmentést.

    Paraméterek:
        screen (pygame.Surface): Render célfelület.
        clock (pygame.time.Clock): FPS szabályozás.
        difficulty_index (int): 0..2.
        player_name (str): Játékosnév pontmentéshez.

    Visszatérés:
        None

    Mellékhatás:
        - Esemény-feldolgozás és rajzolás minden frame-ben.
        - AI mód 3 percenkénti váltása méréshez (hybrid ↔ ml), teljes resetekkel.
        - Pontmentés rekord esetén `assets/csv/scoreboard.csv`-be.

    Folyamat:
        1) initialize_game → kezdő állapot
        2) event loop:
            - ESC: vissza a menübe
            - M: AI mód váltás
            - kézi módban: tanító logok rögzítése (log_example)
        3) update_game_state hívása mód szerint
        4) életvesztés, game over kezelés, ranglista mentés és kirajzolás

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
        """Aktuális mérési mód kulcsa a scores dict-hez."""
        return "hybrid" if use_hybrid else "ml"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            elif event.type == pygame.KEYDOWN and ai_mode is False:
                # csak kézi módban gyűjtünk tanító példákat
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
                        log_example(dx, dy, 0, speed_multiplier, enemy_count)
                    elif event.key == pygame.K_RIGHT:
                        log_example(dx, dy, 1, speed_multiplier, enemy_count)
                    elif event.key == pygame.K_SPACE:
                        log_example(dx, dy, 2, speed_multiplier, enemy_count)

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

            # ellenség betör a sorunkba → életlevonás
            if not game_over and lives == prev_lives and enemy_breached_player_row(player_rect, enemies):
                lives -= 1
                if lives <= 0:
                    scores[_mode_key()] = score
                    print("Végső eredmények (idő előtt):", scores)

                    # Rekord ellenőrzés és mentés assets/csv/scoreboard.csv-be
                    try:
                        is_record = save_score_if_record(player_name, score, str(cfg.SCOREBOARD_CSV))
                    except TypeError:
                        is_record = save_score_if_record(player_name, score)
                    record_msg = f"{player_name}: {score} pont" if is_record else ""

                    try:
                        print_top5(str(cfg.SCOREBOARD_CSV))
                    except TypeError:
                        print_top5()

                    ui.draw_game_over(screen, is_record, record_msg)
                    pygame.time.wait(5000)
                    return

                reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)

            # 3 perc után módváltás és teljes reset a méréshez
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
            # kézi mód
            prev_lives = lives
            lives, game_over, score = update_game_state(
                keys, player_rect, bullets, enemies, all_positions,
                level_data, lives, score, powerups, player_powerups, ai_mode=False,
                player=player_name
            )
            if not game_over and lives == prev_lives and enemy_breached_player_row(player_rect, enemies):
                lives -= 1
                if lives <= 0:
                    try:
                       is_record = save_score_if_record(player_name, score, str(cfg.SCOREBOARD_CSV))
                    except TypeError:
                        is_record = save_score_if_record(player_name, score)
                    record_msg = f"{player_name}: {score} pont" if is_record else ""

                    try:
                        print_top5(str(cfg.SCOREBOARD_CSV))
                    except TypeError:
                        print_top5()

                    ui.draw_game_over(screen, is_record, record_msg)
                    pygame.time.wait(5000)
                    return
                reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)

        # Végső game over ág
        if lives <= 0:
            if ai_mode:
                scores[_mode_key()] = score
                print("Végső eredmények:", scores)

            try:
                is_record = save_score_if_record(player_name, score, str(cfg.SCOREBOARD_CSV))
            except TypeError:
                is_record = save_score_if_record(player_name, score)
            record_msg = f"{player_name}: {score} pont" if is_record else ""

            try:
                print_top5(str(cfg.SCOREBOARD_CSV))
            except TypeError:
                print_top5()

            ui.draw_game_over(screen, is_record, record_msg)
            pygame.time.wait(5000)
            return

        # Frame kirajzolása
        ui.draw_game(screen, player_img, player_rect, enemies, bullets, powerups,
                     level_data["level"], lives, heart_img, score, ai_mode)
        clock.tick(60)


def main() -> None:
    """Belépési pont. Pygame init, ranglista CSV init, menü és játékhurok futtatása.

    Paraméterek:
        Nincsenek.

    Visszatérés:
        None

    Mellékhatás:
        - Pygame init és ablak létrehozása ui.WIDTH × ui.HEIGHT mérettel.
        - Ranglista CSV inicializálása az assets/csv alatt.
        - Végtelen ciklusban menü → játék → menü.

    Kivétel:
        - pygame.error, ha nem sikerül az ablakot létrehozni.
        - CSV init kompatibilitási eltérés esetén (régi csv_helper), a fallback ágat használjuk.

    Példa:
        if __name__ == "__main__":
            main()
    """
    pygame.init()

    # Ranglista CSV inicializálása az assets/csv alatt
    try:
        init_csv(str(cfg.SCOREBOARD_CSV))
    except TypeError:
        init_csv()

    screen = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))  # ui.WIDTH → cfg.WIDTH
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()

    while True:
        difficulty_index, player_name = menu_loop(screen, clock)
        game_loop(screen, clock, difficulty_index, player_name)


if __name__ == "__main__":
    main()
