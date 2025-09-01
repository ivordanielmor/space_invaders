# ui_helper.py
import pygame
from pathlib import Path
from typing import Tuple, List, Dict, Any

"""
UI-segédfüggvények Pygame-hez.

Alapelvek:
- Képek: assets/images (központosítva: config.IMG_DIR / config.image_path)
- CSV-k: assets/csv       (központosítva: config.CSV_DIR / config.SCOREBOARD_CSV)
- A modul csak UI-hoz tartozó betöltést és rajzolást tartalmaz.
- Minden méret/útvonal a config modulból jön; itt nem duplikálunk konstansokat.
"""

# --- Központi konfiguráció (egyetlen forrás) ---
import config as cfg

# Kompatibilitási aliasok (régi kód hivatkozásaihoz)
WIDTH, HEIGHT = cfg.WIDTH, cfg.HEIGHT
ASSETS_DIR: Path = cfg.ASSETS_DIR
IMG_DIR: Path = cfg.IMG_DIR
CSV_DIR: Path = cfg.CSV_DIR
SCOREBOARD_CSV: Path = cfg.SCOREBOARD_CSV


# ---------- Útvonal segédek ----------

def get_image_path(name: str) -> Path:
    """Visszaadja egy kép útvonalát az assets/images mappában.

    Paraméterek:
        name (str): Fájlnév kiterjesztéssel, pl. "player.png".

    Visszatérés:
        Path: assets/images/<name>.

    Mellékhatás:
        Nincs.

    Példa:
        path = get_image_path("enemy.png")
    """
    return Path(cfg.image_path(name))


def get_csv_dir() -> Path:
    """Visszaadja az assets/csv mappa elérési útját.

    Visszatérés:
        Path: assets/csv.

    Példa:
        scores_dir = get_csv_dir()
    """
    return CSV_DIR


def get_scoreboard_csv() -> Path:
    """Visszaadja a ranglista CSV (scoreboard.csv) elérési útját.

    Visszatérés:
        Path: assets/csv/scoreboard.csv.

    Példa:
        csv_path = get_scoreboard_csv()
    """
    return SCOREBOARD_CSV


# ---------- Képkezelés ----------

def tint_image(image: pygame.Surface, tint_color: Tuple[int, int, int]) -> pygame.Surface:
    """Színezést alkalmaz egy képre per-pixel módszerrel.

    Paraméterek:
        image (pygame.Surface): Forrás kép. Alpha-csatornás felület ajánlott (convert_alpha).
        tint_color (Tuple[int,int,int]): RGB triple 0..255 komponensekkel.

    Visszatérés:
        pygame.Surface: Új, áttintelt felület. Az eredeti változatlan marad.

    Mellékhatás:
        - Minden nem teljesen átlátszó pixelt az adott tint színre állít,
          az eredeti alfa megtartásával.
        - Nagy képeken lassú lehet, mert Python-szintű per-pixel művelet.

    Kivétel:
        ValueError: ha a színkomponensek kívül esnek a 0..255 tartományon.

    Példa:
        tinted = tint_image(enemy_img, (255, 0, 0))
    """
    if any(c < 0 or c > 255 for c in tint_color):
        raise ValueError("tint_color komponenseknek 0..255 között kell lenniük")
    tinted_image = image.copy()
    w, h = image.get_width(), image.get_height()
    for x in range(w):
        for y in range(h):
            px = image.get_at((x, y))
            if px.a != 0:
                tinted_image.set_at((x, y), pygame.Color(*tint_color, px.a))
    return tinted_image


def _load_image(name: str) -> pygame.Surface:
    """Kép betöltése az assets/images mappából alfa csatornával.

    Paraméterek:
        name (str): A képfájl neve, pl. "heart.png".

    Visszatérés:
        pygame.Surface: Betöltött kép `convert_alpha()`-val.

    Mellékhatás:
        - Fájlrendszer-hozzáférés az assets/images alatt.
        - Hiányzó/sérült fájlnál `pygame.error` vagy `FileNotFoundError`.

    Példa:
        img = _load_image("player.png")
    """
    path = get_image_path(name)
    img = pygame.image.load(str(path)).convert_alpha()
    return img


def load_player() -> Tuple[pygame.Surface, pygame.Rect]:
    """Játékos sprite betöltése és kezdőpozicionálása.

    Visszatérés:
        (pygame.Surface, pygame.Rect): Kétszeresére skálázott sprite és Rect,
        amelynek `midbottom` pozíciója: (WIDTH // 2, HEIGHT - 50).

    Mellékhatás:
        - Olvas a fájlrendszerből, skáláz, Rect-et készít.

    Példa:
        player_img, player_rect = load_player()
    """
    img = _load_image("player.png")
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT - 50)
    return img, rect


def load_enemy() -> pygame.Surface:
    """Ellenség sprite betöltése.

    Visszatérés:
        pygame.Surface: Betöltött ellenség sprite alfa csatornával.

    Példa:
        enemy_img = load_enemy()
    """
    return _load_image("enemy_spinvaders.png")


def load_heart() -> pygame.Surface:
    """Élet ikon betöltése és 32×32-re méretezése.

    Visszatérés:
        pygame.Surface: 32×32-re skálázott szív ikon.

    Példa:
        heart_img = load_heart()
    """
    img = _load_image("heart.png")
    return pygame.transform.smoothscale(img, (32, 32))


def load_powerup_image(name_or_path: str) -> pygame.Surface:
    """Power-up sprite betöltése és 32×32-re méretezése.

    Paraméterek:
        name_or_path (str): Fájlnév (assets/images alól) vagy tetszőleges elérési út.

    Visszatérés:
        pygame.Surface: 32×32 méretű power-up sprite.

    Példa:
        p_img = load_powerup_image("power_speed.png")
        p_img2 = load_powerup_image("assets/images/power_shield.png")
    """
    p = Path(name_or_path)
    if not p.exists():
        p = get_image_path(name_or_path)
    img = pygame.image.load(str(p)).convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))


# ---------- UI rajzolás ----------

def draw_ui(screen: pygame.Surface,
            level: int,
            lives: int,
            heart_img: pygame.Surface,
            score: int,
            ai_mode: bool) -> None:
    """Felhasználói felület (UI) kirajzolása.

    Paraméterek:
        screen: Render célfelület.
        level: Aktuális szint.
        lives: Életek száma.
        heart_img: 32×32-es élet ikon.
        score: Pontszám.
        ai_mode: AI mód jelzése.

    Visszatérés:
        None

    Megjegyzés:
        Feltételezi, hogy a font alrendszer inicializált.
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
    """Teljes jelenet kirajzolása.

    Paraméterek:
        screen: Render cél.
        player_img: Játékos sprite.
        player_rect: Játékos pozíciója.
        enemies: Ellenségek listája {"image","rect"} kulcsokkal.
        bullets: Lövedékek pozíciói [x, y].
        powerups: Power-up sprite-ok csoportja.
        level: Szint.
        lives: Életek.
        heart_img: Élet ikon.
        score: Pontszám.
        ai_mode: AI mód jelzés.

    Visszatérés:
        None

    Mellékhatás:
        - Háttér törlése, elemek kirajzolása, majd `pygame.display.flip()`.
    """
    screen.fill((0, 0, 0))
    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 255), b, cfg.BULLET_RADIUS)
    for e in enemies:
        screen.blit(e["image"], e["rect"])
    powerups.draw(screen)
    screen.blit(player_img, player_rect)
    draw_ui(screen, level, lives, heart_img, score, ai_mode)
    pygame.display.flip()


def draw_game_over(screen: pygame.Surface, is_new_record: bool = False, record_info: str = "") -> None:
    """„GAME OVER” képernyő megjelenítése, ranglista a assets/csv/scoreboard.csv alapján.

    Paraméterek:
        screen: Render cél.
        is_new_record: Új rekord történt-e.
        record_info: Rekord részletező szöveg.

    Visszatérés:
        None

    Megjegyzés:
        A pontokat a csv_helper.load_scores_clean olvassa (ciklikus import elkerülésére lokálisan importálva).
    """
    from csv_helper import load_scores_clean  # lokális import a ciklikus kapcsolatok miatt

    screen.fill((0, 0, 0))

    font_big = pygame.font.SysFont(None, 72)
    game_over_text = font_big.render("GAME OVER", True, (255, 0, 0))
    screen.blit(game_over_text, ((WIDTH - game_over_text.get_width()) // 2, 50))

    y_offset = 150
    if is_new_record and record_info:
        font_record = pygame.font.SysFont(None, 48)
        record_title = font_record.render("ÚJ REKORD!", True, (255, 215, 0))
        screen.blit(record_title, ((WIDTH - record_title.get_width()) // 2, y_offset))
        font_detail = pygame.font.SysFont(None, 32)
        detail_text = font_detail.render(record_info, True, (0, 255, 0))
        screen.blit(detail_text, ((WIDTH - detail_text.get_width()) // 2, y_offset + 60))
        y_offset += 120

    font_small = pygame.font.SysFont(None, 28)
    ranking_title = font_small.render("=== TOP 5 RANGLISTA ===", True, (255, 255, 255))
    screen.blit(ranking_title, ((WIDTH - ranking_title.get_width()) // 2, y_offset))

    try:
        top5 = load_scores_clean(str(SCOREBOARD_CSV))
    except Exception as e:
        print(f"Hiba a pontszámok beolvasásakor: {e}")
        top5 = []

    if not top5:
        info = font_small.render("Még nincs adat a ranglistán.", True, (200, 200, 200))
        screen.blit(info, ((WIDTH - info.get_width()) // 2, y_offset + 40))
    else:
        for i, entry in enumerate(sorted(top5, key=lambda d: d["score"], reverse=True)[:5]):
            player = entry["player"]
            sc = entry["score"]
            score_text = font_small.render(f"{i+1}. {player}: {sc}", True, (255, 255, 255))
            screen.blit(score_text, ((WIDTH - score_text.get_width()) // 2, y_offset + 40 + i * 30))

    pygame.display.flip()


def draw_top5(screen: pygame.Surface, font: pygame.font.Font, font_small: pygame.font.Font) -> None:
    """Top 5 ranglista nézet kirajzolása.

    Paraméterek:
        screen: Render célfelület.
        font: Cím betűtípus.
        font_small: Sorok betűtípusa.

    Visszatérés:
        None

    Megjegyzés:
        A `load_top5` visszaadhat list[tuple] vagy list[dict]-et; mindkettőt kezeli.
    """
    from csv_helper import load_top5  # lokális import

    screen.fill((0, 0, 0))
    title = font.render("Ranglista - TOP 5", True, (255, 255, 255))
    screen.blit(title, ((WIDTH - title.get_width()) // 2, 80))

    try:
        top = load_top5(str(SCOREBOARD_CSV))
    except TypeError:
        top = load_top5()
    except Exception as e:
        print(f"Hiba a TOP5 beolvasásakor: {e}")
        top = []

    if not top:
        msg = font_small.render("Még nincs adat a ranglistán.", True, (200, 200, 200))
        screen.blit(msg, ((WIDTH - msg.get_width()) // 2, HEIGHT // 2))
    else:
        for i, row in enumerate(top, start=1):
            if isinstance(row, dict):
                name, sc = row.get("player", "?"), row.get("score", 0)
            else:
                name, sc = row
            line = font_small.render(f"{i}. {name} — {sc} pont", True, (255, 255, 255))
            screen.blit(line, ((WIDTH - line.get_width()) // 2, 160 + i * 40))

    hint = font_small.render("Esc = vissza a főmenübe", True, (180, 180, 180))
    screen.blit(hint, ((WIDTH - hint.get_width()) // 2, HEIGHT - 60))
    pygame.display.flip()


__all__ = [
    # kompatibilitási exportok
    "WIDTH", "HEIGHT",
    "ASSETS_DIR", "IMG_DIR", "CSV_DIR", "SCOREBOARD_CSV",
    # útvonal segédek
    "get_image_path", "get_csv_dir", "get_scoreboard_csv",
    # képek és UI
    "tint_image",
    "load_player", "load_enemy", "load_heart", "load_powerup_image",
    "draw_ui", "draw_game", "draw_game_over", "draw_top5",
]
