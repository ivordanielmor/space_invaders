"""
Segédszkript: CSV beolvasása, tisztítása és mentése konfiguráció alapján.

Paraméterek:
    nincs

Visszatérés:
    nincs

Kivételek:
    FileNotFoundError: Ha a konfigurációban megadott CSV fájl nem található
    ValueError: Ha a CSV nem tartalmazza a 'player' és 'score' oszlopokat
"""
from typing import Optional
import pandas as pd
from csv_helper import load_and_clean, save_clean_csv
import config as cfg


def main() -> Optional[None]:
    """
    Beolvassa és megtisztítja a CSV fájlt (str(SCOREBOARD_CSV)), ellenőrzi soronként,
    létrehozza a célkönyvtárat, és menti a tisztított fájlt.

    Paraméterek:
        nincs

    Visszatérés:
        Optional[None]: None (nincs visszatérési érték)

    Kivételek:
        FileNotFoundError: Ha a konfigurációban megadott CSV fájl nem található
        ValueError: Ha a CSV nem tartalmazza a szükséges oszlopokat
    """
    # CSV betöltése és tisztítása
    df: pd.DataFrame = load_and_clean(cfg.CSV_PATH)
    
    print(f"Betöltött sorok száma: {len(df)}")
    
    if df.empty:
        print("Nincs adat a mentéshez.")
        return
    
    # DataFrame -> dict lista konverzió
    rows = df.to_dict('records')  # [{"player": "Mór", "score": 1690}, ...]
    
    # Mentés a csv_helper függvényével
    save_clean_csv(rows, "assets/csv/scoreboard_clean.csv")
    
    print(f"Tisztított CSV mentve: assets/csv/scoreboard_clean.csv ({len(df)} sor)")

if __name__ == "__main__":
    main()
