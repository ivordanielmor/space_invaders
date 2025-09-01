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
import os
import pandas as pd
from csv_helper import load_and_clean
import config as cfg


def main() -> Optional[None]:
    """
    Beolvassa és megtisztítja a CSV fájlt (cfg.CSV_PATH), ellenőrzi soronként,
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

    # Ellenőrzés (opcionális)
    for index, row in df.iterrows():
        print(f"{index}: {row.to_dict()}")

    # Könyvtár ellenőrzése és létrehozása, ha nem létezik
    save_dir = os.path.join("assets", "csv")
    os.makedirs(save_dir, exist_ok=True)

    # Fájl mentése a kívánt mappába
    cleaned_path = os.path.join(save_dir, "scoreboard_clean.csv")
    df = df.copy()
    df["score"] = df["score"].astype(int)
    df.to_csv(cleaned_path, index=False, encoding="utf-8")
    print(f"\nTisztított CSV mentve ide: {cleaned_path}")


if __name__ == "__main__":
    main()
