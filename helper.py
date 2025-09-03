"""Játékmenet logika és AI-segédek.

I/O konvenciók:
- Képek az `assets/images` mappából töltődnek a `ui_helper` modulon keresztül.
- CSV-k az `assets/csv` mappában vannak. A tanító példák alapértelmezett fájlja: `assets/csv/examples.csv`.

Felelősségi kör:
- Játékos, lövedékek és ellenségek mozgatása.
- Power-up kezelés.
- Egylépéses állapotfrissítés (update_game_state).
- Szabály-alapú AI döntés (decide_action) és metrikák.

Megjegyzés:
- Minden képernyőméret és egyéb konstans a `config` modulból jön.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any, TypedDict

import csv
import random
import pygame

import config as cfg
import ui_helper as ui


# --- Debug beállítások ---
DEBUG: bool = False
"""Ha True, részletes naplózás történik a konzolra."""

LOG_EVERY_MS: int = 400
"""Legalább ennyi ms teljen el két debug log között."""

_last_log: int = 0
_last_action: Optional[Dict[str, Any]] = None

# --- Állapot a mozgás irányának megtartásához ---
last_move_direction: str = "right"
"""Az utolsó ismert vízszintes mozgásirány. Értékek: "left" | "right"."""


class Action(TypedDict):
    """AI döntés reprezentációja.

    Kulcsok:
        move (Optional[str]): "left" | "right" | "retreat" | None
        shoot (bool): Lőjön-e az aktuális frame-ben.
    """
    move: Optional[str]
    shoot: bool


# --- Gyorsított színezés cache-eléssel (méret+szín szerint) ---

_TINT_CACHE: dict[tuple[int, int, int, int, int, int], pygame.Surface] = {}
"""Kulcs: (id(base_surface), width, height, r, g, b) → tintelt Surface."""


def _tint_image_replace(src: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
    """Per-pixel színezés: az RGB-t `color`-ra állítja, az alfa megmarad.

    Paraméterek:
        src: Forrás felület, alpha csatornával.
        color: (r,g,b), mind 0..255.

    Visszatérés:
        Új felület a beállított színnel.
    """
    r, g, b = color
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise ValueError("A szín komponenseinek 0..255 között kell lenniük")
    out = src.copy()
    w, h = out.get_width(), out.get_height()
    for x in range(w):
        for y in range(h):
            px = out.get_at((x, y))
            if px.a != 0:
                out.set_at((x, y), pygame.Color(r, g, b, px.a))
    return out


def _tinted(base: pygame.Surface, w: int, h: int, color: Tuple[int, int, int]) -> pygame.Surface:
    """Visszaad egy skálázott+tintelt felületet cache-ből vagy legenerálja.

    Cache-kulcs: (id(base), w, h, r, g, b)
    """
    key = (id(base), w, h, color[0], color[1], color[2])
    cached = _TINT_CACHE.get(key)
    if cached is not None:
        return cached
    scaled = pygame.transform.smoothscale(base, (w, h))
    tinted = _tint_image_replace(scaled, color)
    _TINT_CACHE[key] = tinted
    return tinted


class PowerUp(pygame.sprite.Sprite):
    """Power-up entitás. Képet betölt, 32×32-re skáláz, és lejárati idővel bír.

    Attribútumok:
        image (pygame.Surface): A méretezett, átlátszóságot támogató sprite.
        rect (pygame.Rect): Ütköződoboz, középre igazítva.
        type (str): Típus címke (pl. "star").
        spawn_time (int): Létrejövetel időbélyege (`pygame.time.get_ticks()`).
        duration (int): Érvényességi időtartam ms-ban.

    Paraméterek:
        image_path (str): Képfájl neve vagy útvonala. Ha csak név, az `assets/images` alól olvassuk.
        powerup_type (str): Logikai típus.
        position (Tuple[int, int]): Középpont (x, y) pixelben.
        duration_ms (int): Aktív időtartam ms-ban.

    Kivétel:
        pygame.error / FileNotFoundError: Kép betöltési hiba.
        ValueError: Negatív `duration_ms` esetén.
    """

    def __init__(self, image_path: str, powerup_type: str, position: Tuple[int, int], duration_ms: int) -> None:
        super().__init__()
        if duration_ms < 0:
            raise ValueError("duration_ms nem lehet negatív")
        self.image = ui.load_powerup_image(image_path)
        self.rect = self.image.get_rect(center=position)
        self.type = powerup_type
        self.spawn_time = pygame.time.get_ticks()
        self.duration = duration_ms

    def is_active(self) -> bool:
        """True, ha (now - spawn_time) < duration."""
        return pygame.time.get_ticks() - self.spawn_time < self.duration


def generate_enemy_positions() -> List[Tuple[int, int]]:
    """Ellenség kezdőpozíciók rács alapján.

    Számítás:
        Bal-felső sarok koordináták ROWS×COLS rácsra, a `config`-ban megadott
        offsetekkel és paddinggel. Egy cella 20 px alapszélességgel számol.

    Visszatérés:
        List[Tuple[int,int]]: Pozíciók listája pixelben (bal, felső).
    """
    return [
        (cfg.ENEMY_OFFSET_X + col * (20 + cfg.ENEMY_PADDING_X),
         cfg.ENEMY_OFFSET_Y + row * (20 + cfg.ENEMY_PADDING_Y))
        for row in range(cfg.ROWS) for col in range(cfg.COLS)
    ]


def move_player(rect: pygame.Rect, keys: Any, ai_action: Optional[Action] = None) -> None:
    """Játékos mozgatása billentyűről vagy AI utasítás alapján.

    Paraméterek:
        rect: A játékos rect-je. Helyben módosul.
        keys: `pygame.key.get_pressed()` eredménye vagy ezzel kompatibilis objektum.
        ai_action: Ha megadott és tartalmaz `move`-ot, felülírja a billentyűzetet.

    Mellékhatás:
        - A `rect` koordinátái módosulnak.
        - A képernyőszélekhez igazítás történik (0..WIDTH/HEIGHT).
    """
    if ai_action and ai_action["move"]:
        mv = ai_action["move"]
        if mv in ("left", "right"):
            rect.x += cfg.PLAYER_SPEED * (-1 if mv == "left" else 1)
        elif mv in ("down", "retreat"):
            rect.y += cfg.PLAYER_SPEED
    else:
        if keys and keys[pygame.K_LEFT]:
            rect.x -= cfg.PLAYER_SPEED
        if keys and keys[pygame.K_RIGHT]:
            rect.x += cfg.PLAYER_SPEED
        if keys and keys[pygame.K_DOWN]:
            rect.y += cfg.PLAYER_SPEED

    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, cfg.WIDTH)
    rect.top = max(rect.top, 0)
    rect.bottom = min(rect.bottom, cfg.HEIGHT)


def move_bullets(bullets: List[List[int]]) -> None:
    """Játékos lövedékeinek felfelé mozgatása és képernyőn kívüliek szűrése.

    Paraméterek:
        bullets: [x, y] párok listája. Helyben módosul.
    """
    for b in bullets:
        b[1] -= cfg.BULLET_SPEED
    bullets[:] = [b for b in bullets if b[1] > 0]


def create_enemies(enemy_img: pygame.Surface, all_positions: List[Tuple[int, int]],
                   count: int, speed_multiplier: float = 1.0) -> List[Dict[str, Any]]:
    """Ellenség példányok létrehozása véletlen méret- és szín-paraméterekkel.

    Paraméterek:
        enemy_img: Alap sprite, amelyből skálázunk és színezünk.
        all_positions: Lehetséges kezdőpozíciók.
        count: Létrehozandó ellenségek száma.
        speed_multiplier: Sebességszorzó a nehézséghez.

    Visszatérés:
        List[Dict[str,Any]]: Minden elem tartalmazza:
            - "rect" (pygame.Rect)
            - "speed" (float)
            - "image" (pygame.Surface) – színezett sprite
            - "float_x", "float_y" (float) – subpixel pozíciók

    Megjegyzés:
        A színezés cache-elve van a teljesítmény miatt.
    """
    positions = all_positions[:]  # bemeneti lista nem módosul
    random.shuffle(positions)
    enemies: List[Dict[str, Any]] = []
    for pos in positions[:count]:
        size = random.randint(20, 40)
        color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255),
        )
        tinted_img = _tinted(enemy_img, size, size, color)
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


def reset_level(player_rect: pygame.Rect, bullets: List[List[int]],
                enemies: List[Dict[str, Any]], all_positions: List[Tuple[int, int]],
                level_data: Dict[str, Any], same_level: bool = False) -> None:
    """Szint újraindítása.

    Viselkedés:
        - Ha `same_level=False`, növeli a szintet és az ellenségszámot.
        - Újragenerálja az ellenségeket.
        - Kiüríti a lövedékeket.
        - Játékost visszateszi az alsó középre.
        - Sebességet újraszámolja.

    Paraméterek:
        player_rect, bullets, enemies, all_positions, level_data: Állapotobjektumok.
        same_level: Ha True, nem nő a szintszám és az ellenségszám.
    """
    if not same_level:
        level_data["level"] += 1
        level_data["enemy_count"] += 2
    enemies[:] = create_enemies(
        level_data["enemy_img"],
        all_positions,
        level_data["enemy_count"],
        level_data["speed_multiplier"],
    )
    bullets.clear()
    player_rect.midbottom = (cfg.WIDTH // 2, cfg.HEIGHT - 50)
    level_data["dx"] = 2 * level_data["speed_multiplier"]


def spawn_powerup(powerups: pygame.sprite.Group) -> None:
    """Véletlenszerű 'star' power-up spawn.

    Logika:
        Ha nincs aktív power-up és `random() < 0.001`, akkor létrejön egy 4s élettartamú
        "star" típusú power-up a képernyő belső tartományában.

    Paraméterek:
        powerups: Cél sprite-csoport.
    """
    if len(powerups) == 0 and random.random() < 0.001:
        pos = (random.randint(50, cfg.WIDTH - 50), random.randint(50, cfg.HEIGHT - 150))
        powerup = PowerUp("star.png", "star", pos, 4000)
        powerups.add(powerup)


def update_shoot_delay(player_powerups: Dict[str, int]) -> int:
    """Aktuális lövési késleltetés ms-ban, power-upok figyelembevételével.

    Viselkedés:
        - Ha "star" aktív az elmúlt 4s-ben → `cfg.POWERUP_SHOOT_DELAY`.
        - Lejárt "star" eltávolítása a dict-ből.

    Paraméterek:
        player_powerups: Aktivált power-upok időbélyegei.

    Visszatérés:
        int: Késleltetés ms.
    """
    if "star" in player_powerups:
        if pygame.time.get_ticks() - player_powerups["star"] < 4000:
            return cfg.POWERUP_SHOOT_DELAY
        else:
            del player_powerups["star"]
    return cfg.BASE_SHOOT_DELAY


def handle_shooting(keys: Any, bullets: List[List[int]], player_rect: pygame.Rect,
                    current_time: int, level_data: Dict[str, Any], shoot_delay: int,
                    ai_action: Optional[Action] = None) -> None:
    """Lövés kezelése billentyűzetről vagy AI-ból, késleltetéssel.

    Paraméterek:
        keys: `pygame.key.get_pressed()` eredménye, vagy None AI módban.
        bullets: Lövedéklista. Bővülhet.
        player_rect: A lövedék a játékos tetejéről indul.
        current_time: `pygame.time.get_ticks()`.
        level_data: Tartalmazza a "last_shot_time"-ot.
        shoot_delay: Min. idő két lövés között.
        ai_action: Ha `shoot=True`, akkor lövés kérés AI-ból.
    """
    should_shoot = False

    if ai_action and ai_action.get("shoot", False):
        should_shoot = True
    elif keys and keys[pygame.K_SPACE]:
        should_shoot = True

    if should_shoot and current_time - level_data["last_shot_time"] > shoot_delay:
        bullets.append([player_rect.centerx, player_rect.top])
        level_data["last_shot_time"] = current_time


def handle_bullet_collisions(bullets: List[List[int]], enemies: List[Dict[str, Any]],
                             powerups: pygame.sprite.Group, score: int,
                             player_powerups: Dict[str, int]) -> int:
    """Lövedékek ütközése ellenségekkel és power-upokkal.

    Paraméterek:
        bullets, enemies, powerups, score, player_powerups

    Visszatérés:
        int: Új pontszám (+10 minden kilőtt ellenségért).
    """
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


def remove_expired_powerups(powerups: pygame.sprite.Group) -> None:
    """Lejárt power-upok eltávolítása a csoportból."""
    for powerup in list(powerups):
        if not powerup.is_active():
            powerups.remove(powerup)


def collect_powerups(player_rect: pygame.Rect, powerups: pygame.sprite.Group,
                     player_powerups: Dict[str, int]) -> None:
    """Összegyűjti a játékossal átfedő power-upokat, és időbélyeget rögzít."""
    for powerup in list(powerups):
        if player_rect.colliderect(powerup.rect):
            player_powerups[powerup.type] = pygame.time.get_ticks()
            powerups.remove(powerup)


def move_enemies(enemies: List[Dict[str, Any]], level_data: Dict[str, Any], player_rect: pygame.Rect) -> None:
    """Ellenségek mozgatása ugrásokkal és követéssel. Színkódolás távolság szerint.

    Paraméterek:
        enemies: Ellenség-állapotok listája. Helyben módosul.
        level_data: Tartalmazza az "enemy_img"-et a friss sprite készítéshez.
        player_rect: A játékos helyzete.

    Megjegyzés:
        A sprite minden frame-ben újraszíneződik három kategóriára:
            - közeli: piros
            - közepes: sárga
            - távoli: zöld
        A színezett felületek cache-elve vannak.
    """
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
            enemy["float_x"] += (-jump_distance if random.choice([True, False]) else jump_distance)
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
        enemy["float_x"] = max(0, min(cfg.WIDTH - enemy_width, enemy["float_x"]))
        enemy["float_y"] = max(0, min(cfg.HEIGHT - enemy_height, enemy["float_y"]))

        enemy["rect"].x = int(enemy["float_x"])
        enemy["rect"].y = int(enemy["float_y"])

        if distance < 100:
            color = (255, 0, 0)
        elif distance <= 250:
            color = (255, 255, 0)
        else:
            color = (0, 255, 0)

        enemy["image"] = _tinted(level_data["enemy_img"], enemy_width, enemy_height, color)


def check_player_collision(player_rect: pygame.Rect, enemies: List[Dict[str, Any]]) -> bool:
    """True, ha bármely ellenség rect-je metszi a játékos rect-jét."""
    return any(enemy["rect"].colliderect(player_rect) for enemy in enemies)


def _log_throttled(msg: str, action: Action) -> None:
    """Throttlingos debug log. Új üzenet csak akkor, ha eltelt min. idő és változott az akció.

    Paraméterek:
        msg: Kiírandó szöveg.
        action: Aktuális akció.
    """
    global _last_log, _last_action
    if not DEBUG:
        return
    now = pygame.time.get_ticks()
    if (now - _last_log > LOG_EVERY_MS) and (action != _last_action):
        print(msg)
        _last_log = now
        _last_action = dict(action)


def _nearest_star(player_rect: pygame.Rect, powerups: pygame.sprite.Group) -> Optional[PowerUp]:
    """Vízszintesen legközelebbi 'star' power-up visszaadása, vagy None."""
    stars = [p for p in powerups if getattr(p, "type", None) == "star"]
    if not stars:
        return None
    return min(stars, key=lambda p: abs(p.rect.centerx - player_rect.centerx))


def _enemy_metrics(player_rect: pygame.Rect, enemies: List[Dict[str, Any]]
                   ) -> Tuple[Optional[Dict[str, Any]], Optional[float], Optional[float]]:
    """Legközelebbi ellenség, vízszintes eltérés és távolság meghatározása.

    Visszatérés:
        (enemy, dx, dist): enemy lehet None; dx és dist float vagy None.
    """
    if not enemies:
        return None, None, None
    e = min(
        enemies,
        key=lambda en: ((en["rect"].centerx - player_rect.centerx) ** 2 +
                        (en["rect"].centery - player_rect.centery) ** 2) ** 0.5
    )
    dx = e["rect"].centerx - player_rect.centerx
    dist = (dx ** 2 + (e["rect"].centery - player_rect.centery) ** 2) ** 0.5
    return e, float(dx), float(dist)


def _decide_move_attack(dx: float, dist: float) -> Optional[str]:
    """Támadó mozgásirány kiválasztása a célhoz képest. Frissíti a globális irányt."""
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


def aligned_for_shot(player_rect: pygame.Rect, target_rect: pygame.Rect, extra: int = cfg.AIM_EXTRA) -> bool:
    """True, ha a játékos középvonala a cél hit-box „folyosójában” van.

    Folyosó:
        [target.left - slack, target.right + slack],
        ahol slack = BULLET_RADIUS + extra + target.width//4.
    """
    slack = cfg.BULLET_RADIUS + extra + (target_rect.width // 4)
    return (target_rect.left - slack) <= player_rect.centerx <= (target_rect.right + slack)


def decide_action(player_rect: pygame.Rect, enemies: List[Dict[str, Any]],
                  powerups: pygame.sprite.Group) -> Action:
    """Szabály-alapú AI döntés mozgásra és lövésre.

    Prioritás:
        1) Közeli 'star' → igazodás és lövés.
        2) Ellenség túl közel (<150) → hátrálás, ha igazított, akkor lövés.
        3) Egyébként vízszintes igazítás, találatkor lövés.
        4) Ha nincs döntés, marad az utolsó irány.

    Visszatérés:
        Action: {"move": Optional[str], "shoot": bool}
    """
    global last_move_direction
    action: Action = {"move": None, "shoot": False}

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
    if enemy is not None and dx is not None and dist is not None:
        if dist < 150:
            action["move"] = "retreat"
            if aligned_for_shot(player_rect, enemy["rect"]):
                action["shoot"] = True
            _log_throttled(f"Retreat, d={dist:.1f}, action: {action}", action)
            return action

        action["move"] = _decide_move_attack(dx, dist)
        if aligned_for_shot(player_rect, enemy["rect"]):
            action["shoot"] = True
        _log_throttled(f"Enemy decision, d={dist:.1f}, dx={dx:.1f}, action: {action}", action)
    return action


def enemy_breached_player_row(player_rect: pygame.Rect, enemies: List[Dict[str, Any]]) -> bool:
    """True, ha bármely ellenfél elérte/átlépte a játékos felső élét.

    Szabály:
        Ha `enemy.rect.bottom >= player_rect.top`, akkor sorátlépés történt.
    """
    top_line = player_rect.top
    return any(e["rect"].bottom >= top_line for e in enemies)


def update_game_state(keys,
                      player_rect: pygame.Rect,
                      bullets: List[List[int]],
                      enemies: List[Dict[str, Any]],
                      all_positions: List[Tuple[int, int]],
                      level_data: Dict[str, Any],
                      lives: int,
                      score: int,
                      powerups: pygame.sprite.Group,
                      player_powerups: Dict[str, int],
                      ai_mode: bool,
                      external_ai_action: Optional[Action] = None,
                      player: str = "Player") -> Tuple[int, bool, int]:
    """Egy frame állapotfrissítése: mozgás, lövés, ütközések, szintváltás.

    Paraméterek:
        keys: `pygame.key.get_pressed()` eredménye.
        player_rect (pygame.Rect)
        bullets (List[List[int]])
        enemies (List[Dict])
        all_positions (List[Tuple[int,int]])
        level_data (Dict[str,Any]): "enemy_img", "enemy_count", "speed_multiplier",
            "last_shot_time", "dx", "level".
        lives (int)
        score (int)
        powerups (pygame.sprite.Group)
        player_powerups (Dict[str,int])
        ai_mode (bool)
        external_ai_action (Optional[Action])
        player (str): Játékos név (jelenleg csak naplózáshoz használható).

    Visszatérés:
        Tuple[int, bool, int]: (lives, game_over, score)
    """
    current_time = pygame.time.get_ticks()
    ai_action = external_ai_action if ai_mode else None
    if ai_mode and ai_action is None:
        ai_action = decide_action(player_rect, enemies, powerups)

    move_player(player_rect, keys, ai_action)
    spawn_powerup(powerups)
    shoot_delay = update_shoot_delay(player_powerups)
    handle_shooting(keys, bullets, player_rect, current_time, level_data, shoot_delay, ai_action)
    move_bullets(bullets)
    score = handle_bullet_collisions(bullets, enemies, powerups, score, player_powerups)
    remove_expired_powerups(powerups)
    collect_powerups(player_rect, powerups, player_powerups)
    move_enemies(enemies, level_data, player_rect)

    SAFE_BASELINE = cfg.HEIGHT - 50
    if ai_mode and player_rect.bottom > SAFE_BASELINE:
        player_rect.y -= 1

    if enemy_breached_player_row(player_rect, enemies):
        lives -= 1
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
    elif check_player_collision(player_rect, enemies):
        lives -= 1
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=True)
    elif not enemies:
        reset_level(player_rect, bullets, enemies, all_positions, level_data, same_level=False)

    return lives, lives <= 0, score


def closest_enemy_center(player_rect: pygame.Rect, enemies: List[Dict[str, Any]]) -> Optional[Tuple[int, int]]:
    """Legközelebbi ellenség középpontja (cx, cy), vagy None, ha nincs ellenség."""
    if not enemies:
        return None
    target = min(enemies, key=lambda e: abs(e["rect"].centerx - player_rect.centerx))
    return target["rect"].centerx, target["rect"].centery


def log_example(dx: float, dy: float, action: int, speed_multiplier: float, enemy_count: int,
                path: str = str(Path(cfg.CSV_DIR) / "examples.csv")) -> None:
    """Tanító példa hozzáfűzése CSV-hez. Fejlécet is ír, ha új fájl.

    Oszlopok:
        dx, dy, action, speed_multiplier, enemy_count

    Paraméterek:
        dx (float): enemy.centerx - player.centerx
        dy (float): enemy.centery - player.centery
        action (int): 0=balra, 1=jobbra, 2=lő
        speed_multiplier (float)
        enemy_count (int)
        path (str): Cél CSV útvonal. Alap: assets/csv/examples.csv
    """
    file_path = Path(path)
    write_header = not file_path.exists() or file_path.stat().st_size == 0
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["dx", "dy", "action", "speed_multiplier", "enemy_count"])
        w.writerow([dx, dy, action, speed_multiplier, enemy_count])


def debug_print(*args, **kwargs) -> None:
    """Feltételes print a globális DEBUG alapján."""
    if DEBUG:
        print(*args, **kwargs)

__all__ = [
    "Action",
    "PowerUp",
    "generate_enemy_positions",
    "move_player",
    "move_bullets",
    "create_enemies",
    "reset_level",
    "spawn_powerup",
    "update_shoot_delay",
    "handle_shooting",
    "handle_bullet_collisions",
    "remove_expired_powerups",
    "collect_powerups",
    "move_enemies",
    "check_player_collision",
    "aligned_for_shot",
    "decide_action",
    "enemy_breached_player_row",
    "update_game_state",
    "closest_enemy_center",
    "log_example",
    "debug_print",
]
