import pygame
import random
import csv
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any, TypedDict

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
BULLET_RADIUS = 5
AIM_EXTRA = 3

# Debug
DEBUG = False
LOG_EVERY_MS = 400
_last_log = 0
_last_action: Optional[Dict[str, Any]] = None

# Állapot
last_move_direction = "right"  # alap vízszintes irány


class Action(TypedDict):
    """AI döntés reprezentációja."""
    move: Optional[str]   # "left" | "right" | "retreat" | None
    shoot: bool


# --- Segédosztályok és segédfüggvények ---

class PowerUp(pygame.sprite.Sprite):
    """Egy játékbeli power-up objektum.

    A példány a létrejöttekor betölti és 32×32-re méretezi a képet, majd
    középre igazítva (`center=position`) állítja be az ütköződobozt.

    Attribútumok:
        image (pygame.Surface): A méretezett, átlátszóságot támogató sprite-kép.
        rect (pygame.Rect): Az ütköződoboz, közepe a `position` koordinátán.
        type (str): A power-up típusa, pl. "rapid_fire", "shield", "double_points".
        spawn_time (int): Létrejövetel időbélyege `pygame.time.get_ticks()`-ből.
        duration (int): Aktív idő ms-ban. Ennyi ideig számít érvényesnek.

    Megjegyzés:
        A `type` név beárnyékolja a beépített `type` függvényt. Ha zavaró, nevezd át
        pl. `powerup_type`-ra a hívó kóddal együtt.
    """

    def __init__(self, image_path: str, type: str, position: Tuple[int, int], duration_ms: int) -> None:
        """Inicializálja a power-upot képpel, típussal, pozícióval és időtartammal.

        Paraméterek:
            image_path (str): Útvonal a képfájlhoz. Alpha-csatornát érdemes használni (PNG).
            type (str): Logikai típuscímke, amelyhez a játék logikát köt (pl. "rapid_fire").
            position (Tuple[int, int]): A sprite középpontjának (x, y) koordinátái pixelben.
            duration_ms (int): Meddig legyen aktív a power-up, ezredmásodpercben.

        Visszatérés:
            None

        Kivétel dobása:
            pygame.error: Ha a képfájl nem tölthető be.
            FileNotFoundError: Ha az `image_path` nem létezik (platformtól függően).
            ValueError: Ha `duration_ms` < 0 vagy a `position` nem 2 elemű egészpár.
        """
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.smoothscale(self.image, (32, 32))
        self.rect = self.image.get_rect(center=position)
        self.type = type
        self.spawn_time = pygame.time.get_ticks()
        self.duration = duration_ms

    def is_active(self) -> bool:
        """Jelzi, hogy a power-up még érvényes-e az időzítés alapján.

        Logika:
            Aktív, ha (aktuális_tick - spawn_time) < duration.

        Paraméterek:
            Nincs.

        Visszatérés:
            bool: True, ha a power-up még aktív. Különben False.

        Megjegyzés:
            Az időzítés a kliens gép `pygame.time.get_ticks()` értékétől függ.
        """
        return pygame.time.get_ticks() - self.spawn_time < self.duration


def tint_image(image: pygame.Surface, tint_color: Tuple[int, int, int]) -> pygame.Surface:
    """Színezést alkalmaz egy képre per-pixel módszerrel.

    Paraméterek:
        image (pygame.Surface): Forráskép alpha-csatornával.
        tint_color (Tuple[int,int,int]): RGB szín, amellyel a nem átlátszó pixeleket színezzük.

    Visszatérés:
        pygame.Surface: Új, megszínezett felület.

    Teljesítmény:
        O(w*h) pixelen iterál. Nagy sprite-oknál drága. Gyártás előtt érdemes cache-elni.

    Kivétel dobása:
        ValueError: Ha `tint_color` bármely komponense 0..255 tartományon kívül esik.
    """
    if any(c < 0 or c > 255 for c in tint_color):
        raise ValueError("tint_color komponenseknek 0..255 között kell lenniük")
    tinted_image = image.copy()
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            pixel = image.get_at((x, y))
            if pixel.a != 0:
                tinted_image.set_at((x, y), pygame.Color(*tint_color, pixel.a))
    return tinted_image


def generate_enemy_positions() -> List[Tuple[int, int]]:
    """Legenerálja az ellenségek kezdőpozícióit rács alapján.

    Paraméterek:
        Nincs. A pozíciók a globális ROWS, COLS, OFFSET és PADDING értékekből számolódnak.

    Visszatérés:
        List[Tuple[int,int]]: Bal-felső sarok koordináták listája pixelben.
    """
    return [
        (ENEMY_OFFSET_X + col * (20 + ENEMY_PADDING_X),
         ENEMY_OFFSET_Y + row * (20 + ENEMY_PADDING_Y))
        for row in range(ROWS) for col in range(COLS)
    ]


def load_player() -> Tuple[pygame.Surface, pygame.Rect]:
    """Betölti a játékos sprite-ot és beállítja a kezdőpozíciót.

    Paraméterek:
        Nincs. A fájlnév: "player.png".

    Visszatérés:
        Tuple[Surface, Rect]: A méretezett kép és a hozzátartozó rect.
        A rect közepe alul: (WIDTH//2, HEIGHT-50).

    Kivétel dobása:
        pygame.error / FileNotFoundError: Ha a fájl nem tölthető be.
    """
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT - 50)
    return img, rect


def load_enemy() -> pygame.Surface:
    """Betölti az ellenség alap sprite-ját.

    Paraméterek:
        Nincs. A fájlnév: "enemy_spinvaders.png".

    Visszatérés:
        pygame.Surface: Alpha-csatornás felület.

    Kivétel dobása:
        pygame.error / FileNotFoundError: Ha a fájl nem tölthető be.
    """
    return pygame.image.load("enemy_spinvaders.png").convert_alpha()


def load_heart() -> pygame.Surface:
    """Betölti és 32×32-re méretezi az élet szimbólumot.

    Paraméterek:
        Nincs. A fájlnév: "heart.png".

    Visszatérés:
        pygame.Surface: Átméretezett felület.

    Kivétel dobása:
        pygame.error / FileNotFoundError: Ha a fájl nem tölthető be.
    """
    img = pygame.image.load("heart.png").convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))


def move_player(rect: pygame.Rect, keys: Any, ai_action: Optional[Action] = None) -> None:
    """Mozgatja a játékost billentyűzettel vagy AI utasítással.

    Paraméterek:
        rect (pygame.Rect): A játékos ütköződoboza. Helyben módosul.
        keys (obj): `pygame.key.get_pressed()` eredménye vagy azzal kompatibilis.
        ai_action (Optional[Action]): AI döntés. Ha meg van adva és tartalmaz `move`-ot,
            felülírja a billentyűzetet.

    Visszatérés:
        None

    Mellékhatás:
        A `rect` koordinátái és a globális képernyőhatárokhoz igazítás.
    """
    if ai_action and ai_action["move"]:
        mv = ai_action["move"]
        if mv in ("left", "right"):
            rect.x += PLAYER_SPEED * (-1 if mv == "left" else 1)
        elif mv in ("down", "retreat"):
            rect.y += PLAYER_SPEED
    else:
        if keys and keys[pygame.K_LEFT]:
            rect.x -= PLAYER_SPEED
        if keys and keys[pygame.K_RIGHT]:
            rect.x += PLAYER_SPEED
        if keys and keys[pygame.K_DOWN]:
            rect.y += PLAYER_SPEED

    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, WIDTH)
    rect.top = max(rect.top, 0)
    rect.bottom = min(rect.bottom, HEIGHT)


def move_bullets(bullets: List[List[int]]) -> None:
    """Felfelé mozgatja a játékos lövedékeit és kilistázza a képernyőn kívülieket.

    Paraméterek:
        bullets (List[List[int]]): [x, y] párok listája. Helyben módosul.

    Visszatérés:
        None
    """
    for b in bullets:
        b[1] -= BULLET_SPEED
    bullets[:] = [b for b in bullets if b[1] > 0]


def create_enemies(enemy_img: pygame.Surface, all_positions: List[Tuple[int, int]],
                   count: int, speed_multiplier: float = 1.0) -> List[Dict[str, Any]]:
    """Létrehozza az ellenségek listáját véletlen mérettel és színnel.

    Paraméterek:
        enemy_img (pygame.Surface): Bázis sprite, amelyből méretezünk és színezünk.
        all_positions (List[Tuple[int,int]]): Elérhető kezdőpozíciók.
        count (int): Létrehozandó ellenségek száma.
        speed_multiplier (float): Sebességszorzó a szint nehezítéséhez.

    Visszatérés:
        List[Dict[str,Any]]: Minden elem kulcsai:
            - "rect" (pygame.Rect): aktuális hely
            - "speed" (float): alap sebesség (nem minden ág használja)
            - "image" (pygame.Surface): aktuális, színezett sprite
            - "float_x" (float), "float_y" (float): subpixel pozíciók

    Megjegyzés:
        A színezés per-pixel történik. Cache-eléssel gyorsítható.
    """
    random.shuffle(all_positions)
    enemies: List[Dict[str, Any]] = []
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


def reset_level(player_rect: pygame.Rect, bullets: List[List[int]],
                enemies: List[Dict[str, Any]], all_positions: List[Tuple[int, int]],
                level_data: Dict[str, Any], same_level: bool = False) -> None:
    """Újraindítja a szintet ellenségekkel és játékossal.

    Paraméterek:
        player_rect (pygame.Rect): Játékos rect. Kezdőpontra állítódik.
        bullets (List[List[int]]): Lövedékek listája. Kiürül.
        enemies (List[Dict]): Ellenségek listája. Újragenerálódik.
        all_positions (List[Tuple[int,int]]): Potenciális ellenségpozíciók.
        level_data (Dict[str,Any]): Állapot: "level", "enemy_count", "speed_multiplier",
            "enemy_img", "dx" stb. Helyben módosul.
        same_level (bool): Ha True, a szintszám és enemy_count nem nő.

    Visszatérés:
        None
    """
    if not same_level:
        level_data["level"] += 1
        level_data["enemy_count"] += 2
    enemies[:] = create_enemies(level_data["enemy_img"], all_positions, level_data["enemy_count"], level_data["speed_multiplier"])
    bullets.clear()
    player_rect.midbottom = (WIDTH // 2, HEIGHT - 50)
    level_data["dx"] = 2 * level_data["speed_multiplier"]


def spawn_powerup(powerups: pygame.sprite.Group) -> None:
    """Véletlenszerűen új power-upot spawnol.

    Paraméterek:
        powerups (pygame.sprite.Group): Cél csoport, ide kerül az új power-up.

    Visszatérés:
        None

    Logika:
        Ha nincs aktív power-up és `random()<0.001`, akkor "star" típusú power-upot hoz létre.
    """
    if len(powerups) == 0 and random.random() < 0.001:
        pos = (random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 150))
        powerup = PowerUp("star.png", "star", pos, 4000)
        powerups.add(powerup)


def update_shoot_delay(player_powerups: Dict[str, int]) -> int:
    """Visszaadja az aktuális lövési késleltetést a power-upok függvényében.

    Paraméterek:
        player_powerups (Dict[str,int]): Power-up aktiválási idők `pygame.time.get_ticks()` alapján.

    Visszatérés:
        int: Lövési késleltetés ms-ban.

    Mellékhatás:
        Lejárt "star" bejegyzés törlődik a szótárból.
    """
    if "star" in player_powerups:
        if pygame.time.get_ticks() - player_powerups["star"] < 4000:
            return POWERUP_SHOOT_DELAY
        else:
            del player_powerups["star"]
    return BASE_SHOOT_DELAY


def handle_shooting(keys: Any, bullets: List[List[int]], player_rect: pygame.Rect,
                    current_time: int, level_data: Dict[str, Any], shoot_delay: int,
                    ai_action: Optional[Action] = None) -> None:
    """Kezeli a lövést billentyűzetről vagy AI-ból.

    Paraméterek:
        keys: `pygame.key.get_pressed()` eredménye, vagy None AI módban.
        bullets (List[List[int]]): Lövedékek listája. Bővülhet.
        player_rect (pygame.Rect): Játékos rect. Felső élről indul a lövedék.
        current_time (int): `pygame.time.get_ticks()`.
        level_data (Dict[str,Any]): Tartalmazza a "last_shot_time" kulcsot.
        shoot_delay (int): Késleltetés ms-ban két lövés között.
        ai_action (Optional[Action]): AI döntés. Ha `shoot` True, az lövést kér.

    Visszatérés:
        None
    """
    should_shoot = False

    # AI lövés
    if ai_action and ai_action.get("shoot", False):
        should_shoot = True
    # Billentyű lövés (csak ha keys nem None!)
    elif keys and keys[pygame.K_SPACE]:
        should_shoot = True

    # Ha tényleg lőni kell és letelt a késleltetés
    if should_shoot and current_time - level_data["last_shot_time"] > shoot_delay:
        bullets.append([player_rect.centerx, player_rect.top])
        level_data["last_shot_time"] = current_time



def handle_bullet_collisions(bullets: List[List[int]], enemies: List[Dict[str, Any]],
                             powerups: pygame.sprite.Group, score: int,
                             player_powerups: Dict[str, int]) -> int:
    """Kezeli a lövedékek ütközéseit ellenségekkel és power-upokkal.

    Paraméterek:
        bullets (List[List[int]]): Játékos lövedékei. Találat esetén törlődnek.
        enemies (List[Dict]): Ellenségek listája. Találat esetén törlődnek.
        powerups (pygame.sprite.Group): Power-up sprite-ok. Találat esetén felvétel.
        score (int): Aktuális pontszám.
        player_powerups (Dict[str,int]): Aktivált power-upok időbélyegei.

    Visszatérés:
        int: Frissített pontszám (+10 ellenségenként).
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
    """Eltávolítja a lejárt power-upokat a sprite-csoportból.

    Paraméterek:
        powerups (pygame.sprite.Group): Forrás csoport.

    Visszatérés:
        None
    """
    for powerup in list(powerups):
        if not powerup.is_active():
            powerups.remove(powerup)


def collect_powerups(player_rect: pygame.Rect, powerups: pygame.sprite.Group,
                     player_powerups: Dict[str, int]) -> None:
    """Begyűjt minden power-upot, amellyel a játékos rect-je átfed.

    Paraméterek:
        player_rect (pygame.Rect): Játékos ütköződoboza.
        powerups (pygame.sprite.Group): Elérhető power-upok.
        player_powerups (Dict[str,int]): Aktivált power-upok időbélyegei. Bővülhet.

    Visszatérés:
        None
    """
    for powerup in list(powerups):
        if player_rect.colliderect(powerup.rect):
            player_powerups[powerup.type] = pygame.time.get_ticks()
            powerups.remove(powerup)


def move_enemies(enemies: List[Dict[str, Any]], level_data: Dict[str, Any], player_rect: pygame.Rect) -> None:
    """Mozgatja az ellenségeket a játékos pozíciójához viszonyítva, ugrásokkal és követéssel.

    Paraméterek:
        enemies (List[Dict]): Ellenség-állapotok listája. Elemek helyben módosulnak.
        level_data (Dict[str,Any]): Tartalmazza az "enemy_img"-et az újraszínezéshez.
        player_rect (pygame.Rect): Játékos helyzete.

    Visszatérés:
        None

    Megjegyzés:
        A függvény minden lépésben újraszínezi a sprite-ot a távolság alapján
        (piros-közeli, sárga-közepes, zöld-távoli).
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
            color = (255, 0, 0)        # közeli
        elif distance <= 250:
            color = (255, 255, 0)      # közepes
        else:
            color = (0, 255, 0)        # távoli

        base_img = pygame.transform.smoothscale(level_data["enemy_img"], (enemy_width, enemy_height))
        enemy["image"] = tint_image(base_img, color)


def check_player_collision(player_rect: pygame.Rect, enemies: List[Dict[str, Any]]) -> bool:
    """Eldönti, hogy a játékos ütközik-e bármely ellenséggel.

    Paraméterek:
        player_rect (pygame.Rect): Játékos ütköződoboza.
        enemies (List[Dict]): Ellenségek listája.

    Visszatérés:
        bool: True, ha bármely ellenség rect-je metszi a játékos rect-jét.
    """
    return any(enemy["rect"].colliderect(player_rect) for enemy in enemies)


def _log_throttled(msg: str, action: Action) -> None:
    """Időkorláttal és állapotváltozásra szűrve kiír debug üzeneteket.

    Paraméterek:
        msg (str): Kiírandó üzenet.
        action (Action): Az aktuális AI akció. Csak akkor logol, ha az előzőtől eltér.

    Visszatérés:
        None

    Megjegyzés:
        Csak akkor aktív, ha DEBUG=True. Minimum LOG_EVERY_MS idő teljen el
        és változzon az `action`.
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
    """Visszaadja a játékoshoz vízszintesen legközelebbi 'star' power-upot.

    Paraméterek:
        player_rect (pygame.Rect): Játékos helyzete.
        powerups (pygame.sprite.Group): Elérhető power-upok.

    Visszatérés:
        Optional[PowerUp]: A legközelebbi 'star', vagy None ha nincs.
    """
    stars = [p for p in powerups if getattr(p, "type", None) == "star"]
    if not stars:
        return None
    return min(stars, key=lambda p: abs(p.rect.centerx - player_rect.centerx))


def _enemy_metrics(player_rect: pygame.Rect, enemies: List[Dict[str, Any]]
                   ) -> Tuple[Optional[Dict[str, Any]], Optional[float], Optional[float]]:
    """Kiszámolja a legközelebbi ellenségre a vízszintes eltérést és a távolságot.

    Paraméterek:
        player_rect (pygame.Rect): Játékos helyzete.
        enemies (List[Dict]): Ellenségek listája.

    Visszatérés:
        Tuple[enemy, dx, dist]:
            enemy (dict|None): Legközelebbi ellenség állapota vagy None.
            dx (float|None): Vízszintes különbség pixelekben (enemy_x - player_x).
            dist (float|None): Euklideszi távolság pixelekben.
    """
    if not enemies:
        return None, None, None
    e = min(enemies, key=lambda en: ((en["rect"].centerx - player_rect.centerx) ** 2 +
                                     (en["rect"].centery - player_rect.centery) ** 2) ** 0.5)
    dx = e["rect"].centerx - player_rect.centerx
    dist = (dx ** 2 + (e["rect"].centery - player_rect.centery) ** 2) ** 0.5
    return e, float(dx), float(dist)


def _decide_move_attack(dx: float, dist: float) -> Optional[str]:
    """Meghatározza a támadó mozgásirányt a célhoz képest.

    Paraméterek:
        dx (float): Cél vízszintes eltérése. Negatív: cél balra.
        dist (float): Távolság a céltól.

    Visszatérés:
        Optional[str]: "left" | "right" vagy None, ha nem kell mozogni.

    Mellékhatás:
        Frissíti a globális `last_move_direction` értéket.
    """
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

def aligned_for_shot(player_rect: pygame.Rect, target_rect: pygame.Rect, extra: int = AIM_EXTRA) -> bool:
    """Igaz, ha a játékos középvonala a cél hit-box folyosójában van.

    A folyosó: [target.left - slack, target.right + slack],
    ahol slack = BULLET_RADIUS + extra + target.width//4 (kicsi sprite-oknál is találjon).
    """
    slack = BULLET_RADIUS + extra + (target_rect.width // 4)
    return (target_rect.left - slack) <= player_rect.centerx <= (target_rect.right + slack)

def decide_action(player_rect: pygame.Rect, enemies: List[Dict[str, Any]],
                  powerups: pygame.sprite.Group) -> Action:
    """AI döntés: mozgás és lövés meghatározása ellenfél és power-upok alapján.

    Prioritások:
        1) Ha van közeli 'star', kövesd és próbálj rálőni.
        2) Ha ellenség túl közel (<150), hátrálj, és ha középen van, lőj.
        3) Egyébként igazodj vízszintben a célhoz, és ha közel középen van, lőj.
        4) Ha nincs döntés, tartsd az utolsó irányt.

    Paraméterek:
        player_rect (pygame.Rect): Játékos helyzete.
        enemies (List[Dict]): Ellenségek listája.
        powerups (pygame.sprite.Group): Power-upok.

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
    """Igaz, ha bármely ellenfél elérte/átlépte a játékos felső élét (sorát).

    Logika:
        Ha bármely ellenség rect.bottom >= player_rect.top, akkor betört a játékos sorába,
        ami azonnali életvesztést eredményez (Space Invaders-szerű szabály).

    Paraméterek:
        player_rect (pygame.Rect): Játékos ütköződoboza.
        enemies (List[Dict[str,Any]]): Ellenségek listája (rect kulccsal).

    Visszatérés:
        bool: True, ha van sorátlépés, különben False.

    Kivétel dobása:
        Nincs.
    """
    top_line = player_rect.top
    return any(e["rect"].bottom >= top_line for e in enemies)


def update_game_state(keys, player_rect, bullets, enemies, all_positions,
                      level_data, lives, score, powerups, player_powerups,
                      ai_mode, external_ai_action=None):
    """Egy frame állapotfrissítése: mozgás, lövés, ütközéskezelés, szintváltás.

    Paraméterek:
        keys: `pygame.key.get_pressed()` eredménye.
        player_rect (pygame.Rect): Játékos pozíciója.
        bullets (List[List[int]]): Játékos lövedékei. Helyben módosulnak.
        enemies (List[Dict]): Ellenségek. Helyben módosulnak.
        all_positions (List[Tuple[int,int]]): Ellenség spawn helyek.
        level_data (Dict[str,Any]): Állapot (enemy_img, enemy_count, speed_multiplier,
            last_shot_time, dx, level, stb.).
        lives (int): Játékos életeinek száma.
        score (int): Pontszám.
        powerups (pygame.sprite.Group): Power-up objektumok.
        player_powerups (Dict[str,int]): Aktivált power-upok és időbélyegeik.
        ai_mode (bool): Ha True, AI vezérli a játékost.
        external_ai_action (Optional[Action]): Külső AI döntés. Ha meg van adva,
            felülírja a belső `decide_action` logikát.

    Visszatérés:
        Tuple[int, bool, int]: (lives, game_over, score)
            - lives (int): Frissített életek
            - game_over (bool): True, ha elfogytak az életek
            - score (int): Frissített pontszám

    Mellékhatás:
        Listák és dict-ek helyben frissülnek. Szint resetelődhet.
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

    SAFE_BASELINE = HEIGHT - 50
    if ai_mode and player_rect.bottom > SAFE_BASELINE:
        player_rect.y -= 1

    # ÚJ: ha az ellenfél elérte a játékos sorát, azonnal életvesztés és reset
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
    """Visszaadja a legközelebbi ellenség középpontjának (cx, cy) koordinátáit.

    Paraméterek:
        player_rect (pygame.Rect): Játékos pozíciója és méretei.
        enemies (List[Dict]): Ellenségek listája, ahol minden ellenség egy szótár, 
            amelynek "rect" kulcsa egy pygame.Rect objektum.

    Visszatérés:
        Optional[Tuple[int, int]]: A legközelebbi ellenség középpontja (cx, cy) 
            koordináták formájában, vagy None, ha nincs ellenség.

    Mellékhatás:
        Nincs. A függvény nem módosít semmilyen bemenetet.
    """
    if not enemies:
        return None
    target = min(enemies, key=lambda e: abs(e["rect"].centerx - player_rect.centerx))
    return target["rect"].centerx, target["rect"].centery

def log_example(dx: float, dy: float, action: int, speed_multiplier: float, enemy_count: int, path: str = "examples.csv") -> None:
    """Hozzáfűz egy példát (dx, dy, action, speed_multiplier, enemy_count) a megadott CSV fájlhoz.

    Paraméterek:
        dx (float): A legközelebbi ellenség vízszintes távolsága a játékostól (enemy.centerx - player.centerx).
        dy (float): A legközelebbi ellenség függőleges távolsága a játékostól (enemy.centery - player.centery).
        action (int): Játékos akciója (0 = balra, 1 = jobbra, 2 = lő).
        speed_multiplier (float): Az ellenségek sebességszorzója (pl. 0.8, 1.0, 1.3).
        enemy_count (int): Az aktuális ellenségek száma.
        path (str): A CSV fájl elérési útja (alapértelmezett: "examples.csv").

    Visszatérés:
        None

    Mellékhatás:
        A megadott CSV fájlba új sor kerül, amely tartalmazza a dx, dy, action, speed_multiplier, enemy_count értékeket.
        Ha a fájl nem létezik vagy üres, a fejléc (dx,dy,action,speed_multiplier,enemy_count) is íródik.
    """
    file_path = Path(path)
    write_header = not file_path.exists() or file_path.stat().st_size == 0
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["dx", "dy", "action", "speed_multiplier", "enemy_count"])
        w.writerow([dx, dy, action, speed_multiplier, enemy_count])

def debug_print(*args, **kwargs) -> None:
    """Feltételes kiírás a terminálra a DEBUG flag alapján.

    Paraméterek:
        *args: Tetszőleges számú pozicionális argumentum, amelyeket ki szeretnénk írni.
        **kwargs: Opcionális kulcs-argumentumok, amelyeket a beépített `print` is támogat 
                  (pl. `sep`, `end`, `file`, `flush`).

    Visszatérés:
        None

    Mellékhatás:
        - Ha a globális `DEBUG` értéke True, a függvény ugyanúgy viselkedik, mint a beépített `print`,
          vagyis a megadott szöveget kiírja a terminálra.
        - Ha a `DEBUG` False, semmilyen kiírás nem történik.
    """
    if DEBUG:
        print(*args, **kwargs)