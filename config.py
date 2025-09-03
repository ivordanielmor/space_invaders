"""Játék-konfiguráció és elérési utak.

Könyvtárstruktúra:
- Képek: assets/images
- CSV-k: assets/csv
- Ranglista: assets/csv/scoreboard.csv

Használat:
- Importálj innen minden globális konstansot (WIDTH, HEIGHT, stb.).
- Fájlutakhoz használd a SCOREBOARD_CSV / CSV_DIR / IMG_DIR értékeket.
- Visszafelé kompatibilitás miatt a CSV_PATH string is elérhető.

Fő konstansok:
- WIDTH, HEIGHT: képernyőméret px.
- PLAYER_SPEED: játékos vízszintes sebessége px/frame.
- BULLET_SPEED: lövedék sebessége px/frame.
- ROWS, COLS: ellenség-rács sorai és oszlopai.
- ENEMY_PADDING_X/Y: ellenségek közti távolság px.
- ENEMY_OFFSET_X/Y: ellenség-rács bal-felső eltolása px.
- COMBO_RADIUS: kombó-közelség sugara px.
- BASE_SHOOT_DELAY: alap lövéskésleltetés ms.
- POWERUP_SHOOT_DELAY: powerup melletti lövéskésleltetés ms.
- BULLET_RADIUS: lövedék sugara px.
- AIM_EXTRA: célzási „folyosó” kiegészítés px.

Helper függvények:
- screen_size() -> (WIDTH, HEIGHT)
- scoreboard_csv_path() -> str
"""

from pathlib import Path
from typing import Tuple

# --- Képernyő és játékmenet konstansok ---
WIDTH: int = 800
HEIGHT: int = 600
PLAYER_SPEED: int = 5
BULLET_SPEED: int = 10
ROWS: int = 4
COLS: int = 5
ENEMY_PADDING_X: int = 10
ENEMY_PADDING_Y: int = 25
ENEMY_OFFSET_X: int = 80
ENEMY_OFFSET_Y: int = 30
COMBO_RADIUS: int = 50
BASE_SHOOT_DELAY: int = 1000
POWERUP_SHOOT_DELAY: int = 300
BULLET_RADIUS: int = 5
AIM_EXTRA: int = 3

# --- Központi elérési utak ---
ASSETS_DIR: Path = Path("assets")
IMG_DIR: Path = ASSETS_DIR / "images"
CSV_DIR: Path = ASSETS_DIR / "csv"
SCOREBOARD_CSV: Path = CSV_DIR / "scoreboard.csv"

# Visszafelé kompatibilis string név (régi kód hivatkozhat rá)
CSV_PATH: str = str(SCOREBOARD_CSV)
HIGHSCORE_PATH = "highscore.json"

def screen_size() -> Tuple[int, int]:
    """Visszaadja a képernyő méretét.

    Visszatérés:
        (int, int): (WIDTH, HEIGHT) képpontban.

    Mellékhatás:
        Nincs.

    Példa:
        w, h = screen_size()
    """
    return WIDTH, HEIGHT

def scoreboard_csv_path() -> str:
    """Visszaadja a ranglista CSV abszolút vagy relatív elérési útját stringként.

    Visszatérés:
        str: Az assets/csv/scoreboard.csv elérési útja.

    Mellékhatás:
        Nincs.

    Példa:
        path = scoreboard_csv_path()
    """
    return str(SCOREBOARD_CSV)

def image_path(name: str) -> str:
    """Visszaadja az assets/images/<name> elérési útját stringként."""
    return str(IMG_DIR / name)