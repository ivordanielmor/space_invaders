import csv
import os
from typing import List, Tuple, Iterable, Mapping, Dict

CSV_PATH = "scoreboard.csv"
DEBUG = True  # állítsd False-ra ha nem akarsz logolást

def debug_print(*args, **kwargs) -> None:
    if DEBUG:
        print(*args, **kwargs)

def init_csv(path: str = CSV_PATH) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["player", "score"])

def save_score(player: str = "Player", score: int = 0, path: str = CSV_PATH) -> None:
    try:
        init_csv(path)
        with open(path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([player, int(score)])
        debug_print(f"Pontszám mentve: {player} - {score}")
    except IOError as e:
        debug_print(f"Hiba a pontszám mentésekor: {e}")

def load_top5(path: str = CSV_PATH) -> List[Tuple[str, int]]:
    """
    Visszaadja a Top 5 (player, score) listát a CSV fájlból.
    (Használható azokhoz az esetekhez, amikor közvetlen tuple-listát akarunk.)
    """
    rows: List[Tuple[str, int]] = []
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
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
                    score = int(score_str)
                except (ValueError, TypeError):
                    continue
                if score < 0:
                    continue
                rows.append((name, score))
    except FileNotFoundError:
        return []

    rows.sort(key=lambda t: t[1], reverse=True)
    return rows[:5]

def save_clean_csv(rows: Iterable[Mapping[str, object]], path: str = "scoreboard_clean.csv") -> None:
    """
    Ment egy listát CSV-be. rows elemei {"player": str, "score": int} formátumúak.
    Felülírja a meglévő fájlt, írja a fejlécet, és minden sornál biztosítja a megfelelő típuskonverziót.
    """
    fieldnames = ["player", "score"]
    # biztosítsuk a könyvtár létezését (ha path könyvtárat is tartalmaz)
    dirn = os.path.dirname(path)
    if dirn:
        os.makedirs(dirn, exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
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
    except IOError as e:
        debug_print(f"Hiba a fájl írása közben: {e}")

def print_top5(path: str = CSV_PATH) -> None:
    """Kiírja a Top 5 listát a konzolra (játékosonként a legjobb pontok)."""
    rows = load_scores_clean(path)
    if not rows:
        print("Még nincs adat a ranglistán.")
        return

    best_map = best_by_player(rows)          # dict[player] = best_score
    sorted_list = to_sorted_list(best_map)   # list[{"player","score"}] csökkenő sorrendben
    top = sorted_list[:5]

    if not top:
        print("Még nincs adat a ranglistán.")
        return

    # mentés tiszta CSV-be (most a rendezett listet mentjük)
    save_clean_csv(top, path="scoreboard_clean.csv")

    print("=== TOP 5 (legjobb pont játékosonként) ===")
    for i, r in enumerate(top, start=1):
        print(f"{i}. {r['player']} — {r['score']} pont")

def load_scores_clean(path: str = CSV_PATH) -> List[dict]:
    """
    Beolvassa a scoreboardot és megtisztítja:
    - üres név → eldob
    - score nem int vagy < 0 → eldob
    - whitespace levágása (strip)
    Visszatér: list[dict]: {"player": str, "score": int}
    """
    rows: List[dict] = []
    if not os.path.exists(path):
        return rows

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            if raw is None:
                continue
            name = (raw.get("player") or "").strip()
            score_str = (raw.get("score") or "").strip()
            if not name:
                continue
            try:
                score = int(score_str)
            except (ValueError, TypeError):
                continue
            if score < 0:
                continue
            rows.append({"player": name, "score": score})
    return rows

def best_by_player(rows: Iterable[dict]) -> Dict[str, int]:
    """rows: iterable of {"player": str, "score": int} -> dict[player] = best_score"""
    best: Dict[str, int] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = (r.get("player") or "").strip()
        try:
            score = int(r.get("score"))
        except Exception:
            continue
        if not name:
            continue
        if name not in best or score > best[name]:
            best[name] = score
    return best

def to_sorted_list(best_map: Dict[str, int]) -> List[dict]:
    """dict -> csökkenő sorrendű lista [{"player":..., "score":...}, ...]."""
    items = [{"player": n, "score": s} for n, s in best_map.items()]
    items.sort(key=lambda x: x["score"], reverse=True)
    return items
