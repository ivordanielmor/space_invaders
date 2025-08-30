import csv
import os
from typing import List, Tuple

CSV_PATH = "scoreboard.csv"

def init_csv():
    """Ha a fájl nem létezik vagy üres, írjuk ki a fejlécet."""
    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["player", "score"])

def save_score(player: str = "Player", score: int = 0):
    """Hozzáfűzi a játékos pontját a scoreboard.csv végéhez."""
    try:
        init_csv()  # Ensure the CSV file is initialized with a header
        with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([player, int(score)])
        print(f"Pontszám mentve: {player} - {score}")  # Debug naplózás
    except IOError as e:
        print(f"Hiba a pontszám mentésekor: {e}")

def load_top5(path: str = CSV_PATH) -> List[Tuple[str, int]]:
    """Visszaadja a Top 5 (player, score) listát a scoreboardból."""
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
    """Kiírja a Top 5 listát a konzolra."""
    top = load_top5(path)
    if not top:
        print("Még nincs adat a ranglistán.")
        return
    print("=== TOP 5 ===")
    for i, (name, score) in enumerate(top, start=1):
        print(f"{i}. {name} — {score} pont")
