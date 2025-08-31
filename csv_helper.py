import csv
import os
from typing import List, Tuple

CSV_PATH = "scoreboard.csv"
DEBUG = True  # Szükséges a debug_print példához; állítsd False-ra ha nem akarod a logolást.

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

def init_csv():
    """Ha a fájl nem létezik vagy üres, írjuk ki a fejlécet.

    Paraméterek:
        Nincsenek (a globális `CSV_PATH` változót használja).

    Visszatérés:
        None

    Mellékhatás:
        - Létrehozza a `CSV_PATH` által megadott fájlt, ha az nem létezik.
        - Ha a fájl létezik, de mérete 0 (üres), akkor is írja bele a fejlécet.
        - A fájl létrehozása/írása során előforduló IOException kivételeket nem kezeli itt,
          hanem a hívó felé engedheti (a jelen implementáció nem dob explicit kivételt).
    Példa:
        init_csv()
    """
    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["player", "score"])

def save_score(player: str = "Player", score: int = 0):
    """Hozzáfűzi a játékos pontját a scoreboard.csv végéhez.

    Paraméterek:
        player (str): A játékos neve, amelyet menteni szeretnénk. Alapértelmezett: "Player".
        score (int): A mentendő pontszám. Alapértelmezett: 0.

    Visszatérés:
        None

    Mellékhatás:
        - Meghívja az `init_csv()`-t, hogy biztosítsa a CSV fejléc meglétét.
        - Megnyitja a `CSV_PATH` fájlt írásra (append módban) és hozzáfűzi a [player, score]
          sort CSV formátumban.
        - Hibák (például I/O hiba) esetén a hibát a konzolra írja (print), de nem dobja tovább.
        - A függvény belsőleg átalakítja az átadott `score` értéket `int`-té; ha ez ValueError-t okoz,
          a kivétel feltehetően kivételként fog jelentkezni (jelen implementáció nem kezeli külön).
    Példa:
        save_score("Alice", 150)
    """
    try:
        init_csv()  # Ensure the CSV file is initialized with a header
        with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([player, int(score)])
        debug_print(f"Pontszám mentve: {player} - {score}")  # Debug naplózás
    except IOError as e:
        debug_print(f"Hiba a pontszám mentésekor: {e}")

def load_top5(path: str = CSV_PATH) -> List[Tuple[str, int]]:
    """Visszaadja a Top 5 (player, score) listát a scoreboardból.

    Paraméterek:
        path (str): Opcionális fájlútvonal, amelyről beolvasni a scoreboardot.
                    Alapértelmezés: a globális `CSV_PATH`.

    Visszatérés:
        List[Tuple[str, int]]: Maximum 5 elemből álló lista, ahol minden elem egy
                               (player: str, score: int) tuple. Ha a fájl nem található,
                               üres listát ad vissza.

    Mellékhatás:
        - Megnyitja és beolvassa a CSV fájlt, átugorva az első sort (fejléc).
        - A CSV minden sorát két mezőre várja; a nem megfelelő sorokat kihagyja.
        - A score mezőt `int`-re konvertálja; ha konverziós hiba történik, az adott sort kihagyja.
        - A beolvasott sorokat pontszám szerint csökkenő sorrendbe rendezi, és visszaadja az első 5-öt.

    Példa:
        top5 = load_top5()
    """
    rows: List[Tuple[str, int]] = []
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # fejléc eldobása
            for row in reader:
                if len(row) != 2:
                    continue
                name, score_str = row
                try:
                    score = int(score_str)
                except ValueError:
                    continue
                rows.append((name, score))
    except FileNotFoundError:
        return []

    rows.sort(key=lambda t: t[1], reverse=True)
    return rows[:5]

def print_top5(path: str = CSV_PATH) -> None:
    """Kiírja a Top 5 listát a konzolra.

    Paraméterek:
        path (str): Opcionális fájlútvonal, amelyről beolvasni a scoreboardot.
                    Alapértelmezés: a globális `CSV_PATH`.

    Visszatérés:
        None

    Mellékhatás:
        - Meghívja a `load_top5(path)`-t és a visszaadott listát formázva kiírja a konzolra.
        - Ha nincs adat, egy erre vonatkozó üzenetet ír ki.
        - A kiírás jelen implementációban a `print`-tel történik; ha preferálod, a
          `debug_print`-et használhatod a felesleges naplózás elkerülésére.

    Példa:
        print_top5()
    """
    top = load_top5(path)
    if not top:
        print("Még nincs adat a ranglistán.")
        return
    print("=== TOP 5 ===")
    for i, (name, score) in enumerate(top, start=1):
        print(f"{i}. {name} — {score} pont")

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
            # raw lehet None vagy dict; biztosítsuk, hogy dict-ként kezeljük
            if raw is None:
                continue

            name = (raw.get("player") or "").strip()
            score_str = (raw.get("score") or "").strip()

            if not name:
                continue  # üres név → kuka

            try:
                score = int(score_str)
            except (ValueError, TypeError):
                continue  # nem szám → kuka

            if score < 0:
                continue  # negatív pont nem oké

            rows.append({"player": name, "score": score})
    return rows

from typing import List, Dict, Iterable

def best_by_player(rows: Iterable[dict]) -> Dict[str, int]:
    """rows: iterable of {"player": str, "score": int} -> dict[player] = best_score"""
    best: Dict[str, int] = {}
    for r in rows:
        # biztonságos kicsomagolás
        name = (r.get("player") if isinstance(r, dict) else None) or ""
        try:
            score = int(r.get("score")) if isinstance(r, dict) else int(r[1])
        except Exception:
            continue  # kihagyjuk a hibás sorokat

        name = name.strip()
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

