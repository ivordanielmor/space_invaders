"""
Főmodul a szezon ranglista futtatásához és megjelenítéséhez.

Paraméterek:
    nincs

Visszatérés:
    nincs

Kivételek:
    ImportError: Ha a csv_helper modul nem található
"""
from typing import Optional
from csv_helper import season_leaderboard
import sys


def main() -> Optional[None]:
    """
    Meghívja a season_leaderboard függvényt, és kiírja a Top 10-et ha van adat.

    Paraméterek:
        nincs

    Visszatérés:
        Optional[None]: None, vagy ha nincs adat, szintén None

    Kivételek:
        ImportError: Ha a csv_helper modul hiányzik
    """
    leaderboard = season_leaderboard()
    if leaderboard is not None:
        print("Szezon ranglista (Top 10):")
        print(leaderboard.head(10))
    else:
        print("Nincs elérhető ranglista.")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"Hiba: nem található a szükséges modul: {e}", file=sys.stderr)
        raise
