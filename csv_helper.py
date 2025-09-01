"""CSV segédfüggvények ranglistához.

Alapértelmezett útvonalak:
- CSV_DIR: assets/csv
- SCOREBOARD_CSV: assets/csv/scoreboard.csv
- CSV_PATH: string kompatibilitási alias a SCOREBOARD_CSV-re

Fő funkciók:
- init_csv: ranglista CSV létrehozása/fejléce
- save_score: nyers pont hozzáfűzése
- load_scores_clean: megtisztított rekordok beolvasása
- best_by_player: játékosonkénti legjobb pont kinyerése
- to_sorted_list: csökkenő sorbarendezés
- load_top5: top5 (tuple formában) gyors lekérdezéshez
- print_top5: top5 kiírása és tiszta CSV mentése
- save_clean_csv: tiszta struktúra mentése (felülír)
- save_score_if_record: csak rekord esetén ment

Megjegyzés:
- Minden függvény paraméterként is fogad útvonalat; ha nem adsz meg,
  az alapértelmezett SCOREBOARD_CSV/CSV_PATH használatban marad.
"""

from __future__ import annotations

import csv
import glob
import pandas as pd
from pathlib import Path
from os import PathLike
from typing import List, Tuple, Iterable, Mapping, Dict, Union
import config as cfg

# --- Útvonal típus alias ---
PathStr = Union[str, PathLike]

# --- Alapértelmezett útvonalak (config opcionális) ---
try:
    from config import CSV_DIR as _CFG_CSV_DIR, SCOREBOARD_CSV as _CFG_SCOREBOARD
    CSV_DIR: Path = Path(_CFG_CSV_DIR)
    SCOREBOARD_CSV: Path = Path(_CFG_SCOREBOARD)
except Exception:
    CSV_DIR = Path("assets") / "csv"
    SCOREBOARD_CSV = CSV_DIR / "scoreboard.csv"

# Log kapcsoló
DEBUG: bool = True  # állítsd False-ra, ha nem akarsz logolást

def load_and_clean(path=cfg.CSV_PATH):
    """
    CSV beolvasása és tisztítása Pandas segítségével.
    
    Paraméterek:
        path (str): A CSV fájl elérési útja
    
    Visszatérés:
        pd.DataFrame: Megtisztított DataFrame 'player' és 'score' oszlopokkal
    
    Kivételek:
        ValueError: Ha nem találhatók a szükséges oszlopok
        FileNotFoundError: Ha a CSV fájl nem található
    """
    try:
        # CSV beolvasása
        df = pd.read_csv(path, encoding="utf-8")
        
        # Egységesítés: keressük a 'player' és 'score' oszlopot, akár eltérő nagybetűzéssel
        cols = {c.lower().strip(): c for c in df.columns}
        player_col = cols.get("player", "player")
        score_col = cols.get("score", "score")
        
        # Ellenőrizzük, hogy megvannak-e a szükséges oszlopok
        if player_col not in df.columns or score_col not in df.columns:
            raise ValueError("A CSV-ben legyen 'player' és 'score' oszlop!")
        
        # Whitespace levágása, pontszám számmá alakítása
        df[player_col] = df[player_col].astype(str).str.strip()
        df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
        
        # Üres nevek, hibás/negatív pontok eldobása
        df = df.dropna(subset=[player_col, score_col])
        df = df[df[player_col] != ""]
        df = df[df[score_col] >= 0]
        
        # Visszaadjuk egységes oszlopnevekkel
        return df.rename(columns={player_col: "player", score_col: "score"})[["player", "score"]]
        
    except FileNotFoundError:
        print(f"A fájl nem található: {path}")
        # Üres DataFrame visszaadása hibás esetben
        return pd.DataFrame(columns=["player", "score"])
    except Exception as e:
        print(f"Hiba történt a fájl feldolgozása során: {e}")
        return pd.DataFrame(columns=["player", "score"])

def debug_print(*args, **kwargs) -> None:
    """Feltételes debug kiírás.

    Paraméterek:
        *args, **kwargs: print-nek átadott paraméterek.

    Visszatérés:
        None

    Mellékhatás:
        - Konzolra ír, ha DEBUG=True.
    """
    if DEBUG:
        print(*args, **kwargs)


def _ensure_parent_dir(path: PathStr) -> None:
    """Gondoskodik a fájl szülőkönyvtárának létezéséről.

    Paraméterek:
        path (str | PathLike): Célfájl elérési útja.

    Visszatérés:
        None

    Mellékhatás:
        - Könyvtárat hoz létre, ha nem létezik.
    """
    d = Path(path).parent
    if str(d):
        d.mkdir(parents=True, exist_ok=True)


def init_csv(path: PathStr = cfg.CSV_PATH) -> None:
    """Inicializálja a ranglista CSV-t, fejlécet ír, ha hiányzik vagy üres.

    Paraméterek:
        path (str | PathLike): A ranglista CSV útvonala. Alap: assets/csv/scoreboard.csv.

    Visszatérés:
        None

    Mellékhatás:
        - Létrehozza a szülőkönyvtárat.
        - Ha a fájl nem létezik vagy üres, fejlécet ír: ["player","score"].

    Példa:
        init_csv()
    """
    _ensure_parent_dir(path)
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        with p.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["player", "score"])


def save_score(player: str = "Player", score: int = 0, path: PathStr = cfg.CSV_PATH) -> None:
    """Nyers pontszám hozzáfűzése a ranglistához.

    Paraméterek:
        player (str): Játékosnév.
        score  (int): Elért pontszám (>=0).
        path   (str | PathLike): CSV útvonal.

    Visszatérés:
        None

    Mellékhatás:
        - Fájlrendszerbe ír, fejlécet biztosít (init_csv).
        - Sor végére fűz egy [player, score] rekordot.

    Kivétel:
        - I/O hibákat lenyeli és debugra logol.
    """
    try:
        init_csv(path)
        with Path(path).open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([player, int(score)])
        debug_print(f"Pontszám mentve: {player} - {score}")
    except OSError as e:
        debug_print(f"Hiba a pontszám mentésekor: {e}")


def load_top5(path: PathStr = cfg.CSV_PATH) -> List[Tuple[str, int]]:
    """Top 5 sor visszaadása (player, score) tuple-listaként.

    Paraméterek:
        path (str | PathLike): CSV útvonal.

    Visszatérés:
        List[Tuple[str,int]]: Legjobb 5 rekord a teljes listából.

    Mellékhatás:
        Nincs.

    Kivétel:
        - Hiányzó fájl esetén üres listát ad.
    """
    rows: List[Tuple[str, int]] = []
    try:
        with Path(path).open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # fejléc eldobása
            for row in reader:
                if len(row) < 2:
                    continue
                name = str(row[0]).strip()
                score_str = str(row[1]).strip()
                if not name:
                    continue
                try:
                    sc = int(score_str)
                except (ValueError, TypeError):
                    continue
                if sc < 0:
                    continue
                rows.append((name, sc))
    except FileNotFoundError:
        return []

    rows.sort(key=lambda t: t[1], reverse=True)
    return rows[:5]


def save_clean_csv(rows: Iterable[Mapping[str, object]],
                   path: PathStr = CSV_DIR / "scoreboard_clean.csv") -> None:
    """Tiszta ranglista mentése felülírással.

    Paraméterek:
        rows: Elemeken kötelező kulcsok: {"player": str, "score": int}.
        path: Cél CSV útvonal. Alap: assets/csv/scoreboard_clean.csv.

    Visszatérés:
        None

    Mellékhatás:
        - Létrehozza a szülőkönyvtárat.
        - Felülírja a célfájlt. Fejlécet ír.

    Kivétel:
        - I/O hibákat debugra logol.
    """
    fieldnames = ["player", "score"]
    _ensure_parent_dir(path)
    try:
        with Path(path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                if not isinstance(r, Mapping):
                    continue
                player = (r.get("player") or "").strip()
                try:
                    score = int(r.get("score"))
                except Exception:
                    continue
                if not player or score < 0:
                    continue
                writer.writerow({"player": player, "score": score})
    except OSError as e:
        debug_print(f"Hiba a fájl írása közben: {e}")


def load_scores_clean(path: PathStr = cfg.CSV_PATH) -> List[dict]:
    """Ranglista beolvasása és megtisztítása.

    Szabályok:
        - Üres név → eldob
        - Nem egész vagy <0 score → eldob
        - Whitespace vágása (strip)

    Paraméterek:
        path (str | PathLike): CSV útvonal.

    Visszatérés:
        List[dict]: {"player": str, "score": int} rekordok.
    """
    rows: List[dict] = []
    p = Path(path)
    if not p.exists():
        return rows

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            if raw is None:
                continue
            name = (raw.get("player") or "").strip()
            score_str = (raw.get("score") or "").strip()
            if not name:
                continue
            try:
                sc = int(score_str)
            except (ValueError, TypeError):
                continue
            if sc < 0:
                continue
            rows.append({"player": name, "score": sc})
    return rows

def best_by_player(rows: Iterable[dict]) -> Dict[str, int]:
    """Játékosonként a legjobb pont meghatározása.

    Paraméterek:
        rows: {"player": str, "score": int} rekordok.

    Visszatérés:
        Dict[str,int]: player → best_score.
    """
    best: Dict[str, int] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = (r.get("player") or "").strip()
        try:
            sc = int(r.get("score"))
        except Exception:
            continue
        if not name:
            continue
        if name not in best or sc > best[name]:
            best[name] = sc
    return best


def to_sorted_list(best_map: Dict[str, int]) -> List[dict]:
    """Dict → csökkenő listává alakítás.

    Paraméterek:
        best_map: player → best_score.

    Visszatérés:
        List[dict]: [{"player":..., "score":...}, ...] pont szerint csökkenően.
    """
    items = [{"player": n, "score": s} for n, s in best_map.items()]
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def print_top5(path: PathStr = cfg.CSV_PATH) -> None:
    """Top 5 kiírása és tiszta CSV mentése ugyanabba a könyvtárba.

    Paraméterek:
        path (str | PathLike): Forrás ranglista CSV.

    Visszatérés:
        None

    Mellékhatás:
        - Konzolra írja a TOP5-öt.
        - Ment egy 'scoreboard_clean.csv' fájlt ugyanabba a könyvtárba.
    """
    rows = load_scores_clean(path)
    if not rows:
        print("Még nincs adat a ranglistán.")
        return

    best_map = best_by_player(rows)
    sorted_list = to_sorted_list(best_map)
    top = sorted_list[:5]

    if not top:
        print("Még nincs adat a ranglistán.")
        return

    clean_path = Path(path).parent / "scoreboard_clean.csv"
    save_clean_csv(top, path=clean_path)

    print("=== TOP 5 (legjobb pont játékosonként) ===")
    for i, r in enumerate(top, start=1):
        print(f"{i}. {r['player']} — {r['score']} pont")


def save_score_if_record(player: str = "Player", score: int = 0, path: PathStr = cfg.CSV_PATH) -> bool:
    """Csak rekord esetén ment új pontot a CSV-be.

    Paraméterek:
        player (str): Játékos neve.
        score  (int): Elért pontszám.
        path   (str | PathLike): Ranglista CSV útvonal.

    Visszatérés:
        bool: True, ha új rekord és mentett; False, ha nem mentett.

    Mellékhatás:
        - Fájlrendszerbe írhat. Debug üzeneteket adhat.

    Hibaeset:
        - Váratlan hiba esetén ment biztonsági okból, és True-val tér vissza.
    """
    try:
        existing_scores = load_scores_clean(path)
        best_scores = best_by_player(existing_scores)
        current_best = best_scores.get(player, -1)  # ha nincs még pontja, -1
        if score > current_best:
            save_score(player, score, path)
            debug_print(
                f"ÚJ REKORD! {player}: {score} pont "
                f"(előző legjobb: {current_best if current_best >= 0 else 'nincs'})"
            )
            return True
        else:
            debug_print(f"Nem rekord. {player}: {score} pont (jelenlegi legjobb: {current_best})")
            return False
    except Exception as e:
        debug_print(f"Hiba a rekord ellenőrzése során: {e}")
        save_score(player, score, path)
        return True

def best_per_player(df: pd.DataFrame) -> pd.DataFrame:
    """
    Játékosonként kiválasztja az egyéni legmagasabb pontszámokat és rangsorol.

    Paraméterek:
        df (pd.DataFrame): Legalább 'player' és 'score' oszlopokat tartalmazó DataFrame

    Visszatérés:
        pd.DataFrame: 'player', 'score' és 'rank' oszlopokat tartalmazó DataFrame,
                      rendezve csökkenő pontszám szerint

    Kivételek:
        ValueError: Ha a bemeneti DataFrame nem tartalmazza a szükséges oszlopokat
    """
    if not {"player", "score"}.issubset(df.columns):
        raise ValueError("A DataFrame-nek tartalmaznia kell a 'player' és 'score' oszlopokat.")
    best = df.groupby("player", as_index=False)["score"].max()
    best = best.sort_values(by="score", ascending=False, ignore_index=True)
    best["rank"] = best.index + 1  # 1-től rangsorolunk
    return best

def merge_scoreboards(pattern: str = "assets/csv/scoreboard_day*.csv") -> Optional[pd.DataFrame]:
    """
    Összefűzi a mintának megfelelő CSV fájlokat, megtisztítja és kiválasztja
    játékosonként a legjobb pontszámokat. Ment CSV és HTML formátumban.

    Paraméterek:
        pattern (str): Glob mintázat a beolvasandó fájlokhoz

    Visszatérés:
        Optional[pd.DataFrame]: A mergeelt és feldolgozott DataFrame, vagy None ha nincs fájl

    Kivételek:
        FileNotFoundError: Ha egy adott fájl nem található (egyedi olvasáskor dobható)
    """
    parts = []
    for path in glob.glob(pattern):
        try:
            part = load_and_clean(path)
            parts.append(part)
            print(f"Beolvasva: {path} (sorok: {len(part)})")
        except FileNotFoundError:
            print(f"Kihagyva (nem található): {path}")
        except Exception as e:
            print(f"Kihagyva {path}: {e}")

    if not parts:
        print("Nem találtam illeszkedő fájlt.")
        return None

    merged = pd.concat(parts, ignore_index=True)
    merged_best = best_per_player(merged)

    # Mentés
    merged_best.to_csv("assets/csv/leaderboard_merged_best.csv", index=False, encoding="utf-8")
    merged_best.to_html("assets/html/leaderboard_merged_best.html", index=False)
    print("Mentve: assets/csv/leaderboard_merged_best.csv, assets/html/leaderboard_merged_best.html")
    return merged_best

def add_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hozzáad egy 'tier' oszlopot pontszám alapján (Bronz/Ezüst/Arany).

    Paraméterek:
        df (pd.DataFrame): Legalább 'score' oszlopot tartalmazó DataFrame

    Visszatérés:
        pd.DataFrame: A bemeneti DataFrame 'tier' oszloppal kiegészítve

    Kivételek:
        ValueError: Ha a 'score' oszlop hiányzik
    """
    if "score" not in df.columns:
        raise ValueError("A DataFrame-nek tartalmaznia kell a 'score' oszlopot.")
    # Példa ponttartományokra: testreszabhatod!
    bins = [-1, 500, 1000, 10**9]   # 0–500 Bronz, 501–1000 Ezüst, >1000 Arany
    labels = ["Bronz", "Ezüst", "Arany"]
    df = df.copy()
    df["tier"] = pd.cut(df["score"], bins=bins, labels=labels)
    return df

def season_leaderboard() -> Optional[pd.DataFrame]:
    """
    Elkészíti a szezon ranglistát: összefűzi a napi scoreboardokat, kiválasztja
    játékosonként a legjobb pontokat, kategorizál és menti a fájlokat.

    Paraméterek:
        nincs

    Visszatérés:
        Optional[pd.DataFrame]: A szezon ranglista DataFrame-je, vagy None ha nincs adat
    """
    merged_best = merge_scoreboards("assets/csv/scoreboard_day*.csv")
    if merged_best is None:
        return None

    leaderboard = add_tiers(merged_best)
    leaderboard.to_csv("assets/csv/season_leaderboard.csv", index=False, encoding="utf-8")
    leaderboard.to_html("assets/csv/season_leaderboard.html", index=False)
    print("Mentve: assets/csv/season_leaderboard.csv, assets/csv/season_leaderboard.html")
    return leaderboard

if __name__ == "__main__":
    # Beolvassuk a scoreboard-ot
    try:
        df = load_and_clean("assets/csv/scoreboard.csv")
    except FileNotFoundError:
        print("A fájl nem található: assets/csv/scoreboard.csv")
        df = None

    if df is not None:
        # Legjobb pontok játékosonként
        best = best_per_player(df)
        print(best.head(10))

        # Mentés fájlba
        best.to_csv("assets/csv/leaderboard_best.csv", index=False, encoding="utf-8")
        best.to_html("assets/html/leaderboard_best.html", index=False)
        print("Mentve: assets/csv/leaderboard_best.csv, assets/html/leaderboard_best.html")
