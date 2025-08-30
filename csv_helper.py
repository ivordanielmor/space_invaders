import csv
import os

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
