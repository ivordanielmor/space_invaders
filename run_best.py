"""
Főszkript: scoreboard beolvasása, tisztítása, legjobb pontok játékosonként és mentés.

Paraméterek:
    nincs

Visszatérés:
    nincs

Kivételek:
    FileNotFoundError: Ha a scoreboard CSV nem található
    ValueError: Ha a CSV nem tartalmazza a szükséges oszlopokat
"""
from typing import Optional
import pandas as pd
from csv_helper import load_and_clean, best_per_player


def main() -> Optional[None]:
    """
    Végrehajtja a következő lépéseket:
      1) Beolvassa és megtisztítja a scoreboard CSV-t
      2) Kiszámolja játékosonként a legjobb pontokat és rangsorolja
      3) Kiírja a Top 10-et és elmenti CSV/HTML formátumban

    Paraméterek:
        nincs

    Visszatérés:
        Optional[None]: None (nincs visszatérési érték)

    Kivételek:
        FileNotFoundError: Ha a megadott CSV fájl nem található
        ValueError: Ha a CSV nem tartalmazza a 'player' és 'score' oszlopokat
    """
    # 1) Tisztított adatok beolvasása
    df: pd.DataFrame = load_and_clean("assets/csv/scoreboard.csv")
    print("Tisztított adatok sorainak száma:", len(df))
    print(df.head())

    # 2) Legjobb pont játékosonként + ranglista
    best: pd.DataFrame = best_per_player(df)
    print("\nTop 10 játékos a legjobb pont alapján:")
    print(best.head(10))

    # 3) Mentés fájlokba
    best_path_csv = "assets/csv/leaderboard_best.csv"
    best_path_html = "assets/html/leaderboard_best.html"
    best.to_csv(best_path_csv, index=False, encoding="utf-8")
    best.to_html(best_path_html, index=False)
    print(f"\nMentve: {best_path_csv}, {best_path_html}")


if __name__ == "__main__":
    main()
