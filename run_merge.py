"""
Főszkript: napi scoreboard fájlok összefűzése és a legjobb pontok megjelenítése.

Paraméterek:
    nincs

Visszatérés:
    nincs

Kivételek:
    ImportError: Ha a csv_helper modul nem található
"""
from typing import Optional
import sys
from csv_helper import merge_scoreboards


def main() -> Optional[None]:
    """
    Meghívja a merge_scoreboards függvényt, kiírja a Top 10-et, ha van adat.

    Paraméterek:
        nincs

    Visszatérés:
        Optional[None]: None (nincs visszatérési érték)

    Kivételek:
        ImportError: Ha a csv_helper modul hiányzik
    """
    merged_best = merge_scoreboards()
    if merged_best is not None:
        print("Globális ranglista (Top 10):")
        print(merged_best.head(10))
    else:
        print("Nincs elérhető összefűzött ranglista.")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"Hiba: nem található a szükséges modul: {e}", file=sys.stderr)
        raise
