from typing import Optional, Dict, Any
import config as cfg
"""
Alap statisztikák készítése a TISZTÍTOTT Space Invaders pontszámokból.

Funkcionalitás:
- TISZTÍTOTT CSV beolvasása (scoreboard_clean.csv)
- JSON beolvasása (highscore.json) 
- Játékosonkénti összegzés: átlag, medián, legjobb, játékszám
- Gyors áttekintés az eredményekről
- Top 3 ranglista kiírása emoji-kkal

Előfeltételek:
- Előbb fusd le: python run_load_csv.py (tisztítás)
- Szükséges fájlok: assets/csv/scoreboard_clean.csv, highscore.json

Kimenet:
- Konzolra írja a statisztikákat
- CSV és JSON összegzés
- Játékosonkénti részletes statisztikák
- Top 3 játékos kiemelése

Hibakezelés:
- Hiányzó fájlok esetén üres adatokkal folytatja
- Hiányzó oszlopok ellenőrzése
- Numerikus konverzió hibák kezelése

Használat:
    python run_stats.py

Példa kimenet:
    🎮 SPACE INVADERS STATISZTIKÁK
    📊 Tisztított CSV adatok:
       - Összes játék: 17
       - Játékosok száma: 6
    👥 JÁTÉKOSONKÉNTI STATISZTIKÁK:
    🥇 Mór: 1690 pont (6 játék)
    🥈 Player: 510 pont (4 játék)
"""

import pandas as pd
import json
import os
from typing import Optional, Dict, Any
import config as cfg

def load_csv_data() -> pd.DataFrame:
    """Betölti a TISZTÍTOTT scoreboard CSV fájlt."""
    clean_csv_path = cfg.CSV_DIR / "scoreboard_clean.csv"
    
    try:
        # TISZTÍTOTT CSV beolvasása
        df = pd.read_csv(clean_csv_path, encoding="utf-8")
        print(f"✅ Tisztított CSV betöltve: {len(df)} sor")
        return df
    except FileNotFoundError:
        print(f"❌ Tisztított CSV fájl nem található: {clean_csv_path}")
        print(f"💡 Futtasd előbb: python run_load_csv.py")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ CSV beolvasási hiba: {e}")
        return pd.DataFrame()

def load_json_data() -> Dict[str, Any]:
    """Betölti a highscore JSON fájlt."""
    try:
        with open(cfg.HIGHSCORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✅ JSON betöltve: {len(data)} rekord")
        return data
    except FileNotFoundError:
        print(f"❌ JSON fájl nem található: {cfg.HIGHSCORE_PATH}")
        return {}
    except Exception as e:
        print(f"❌ JSON beolvasási hiba: {e}")
        return {}

def calculate_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Kiszámolja a játékosonkénti statisztikákat."""
    if df.empty:
        print("❌ Nincs adat a statisztikákhoz")
        return pd.DataFrame()
    
    # Ellenőrizzük, hogy vannak-e a szükséges oszlopok
    required_cols = ["player", "score"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"❌ Hiányzó oszlopok: {missing_cols}")
        return pd.DataFrame()
    
    # Score oszlop számra konvertálása
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["score"])
    
    # Statisztikák számítása
    stats = df.groupby("player", as_index=False)["score"].agg(
        atlag="mean",
        median="median", 
        best="max",
        meresek_szama="count"
    )
    
    # Kerekítés az átlagnál és mediánnál
    stats["atlag"] = stats["atlag"].round(1)
    stats["median"] = stats["median"].round(1)
    
    # Rendezés legjobb pontszám szerint
    stats = stats.sort_values("best", ascending=False)
    
    return stats

def print_summary(df: pd.DataFrame, json_data: Dict[str, Any], stats: pd.DataFrame) -> None:
    """Kiírja az összegzést."""
    print("\n" + "="*50)
    print("🎮 SPACE INVADERS STATISZTIKÁK")
    print("="*50)
    
    # CSV összegzés
    if not df.empty:
        print(f"📊 Tisztított CSV adatok:")
        print(f"   - Összes játék: {len(df)}")
        print(f"   - Játékosok száma: {df['player'].nunique()}")
        print(f"   - Legmagasabb pontszám: {df['score'].max()}")
        print(f"   - Átlagos pontszám: {df['score'].mean():.1f}")
    
    # JSON összegzés  
    if json_data:
        print(f"\n💾 JSON adatok:")
        print(f"   - Rekordok száma: {len(json_data)}")
        if "highscore" in json_data:
            print(f"   - Jelenlegi rekord: {json_data['highscore']}")
    
    # Játékosonkénti statisztikák
    if not stats.empty:
        print(f"\n👥 JÁTÉKOSONKÉNTI STATISZTIKÁK:")
        print("-" * 50)
        print(stats.to_string(index=False))
        
        # Top 3 játékos kiemelése
        print(f"\n🏆 TOP 3 JÁTÉKOS:")
        top3 = stats.head(3)
        for i, row in enumerate(top3.itertuples(), 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            print(f"   {emoji} {row.player}: {row.best} pont ({row.meresek_szama} játék)")

def main() -> Optional[None]:
    """Főfüggvény: betöltés és statisztikák készítése."""
    print("🚀 Statisztikák készítése...")
    
    # Adatok betöltése - HIBAKEZELÉS NÉLKÜL
    df = load_csv_data()
    json_data = load_json_data()
    
    # Statisztikák számítása
    stats = calculate_player_stats(df)
    
    # Összegzés kiírása
    print_summary(df, json_data, stats)
    
    print(f"\n✅ Statisztikák elkészültek!")

if __name__ == "__main__":
    main()