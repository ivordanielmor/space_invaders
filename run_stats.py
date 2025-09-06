"""
Alap statisztikák készítése a TISZTÍTOTT Space Invaders pontszámokból.

Funkcionalitás:
- TISZTÍTOTT CSV beolvasása (scoreboard_clean.csv)
- Highscore JSON beolvasása és összevetés 
- Játékosonkénti összegzés: átlag, medián, legjobb, játékszám
- Javulási analízis: első pont vs referencia pont
- Top 3 ranglista kiírása

Előfeltételek:
- Előbb fusd le: python run_load_csv.py (tisztítás)
- Szükséges fájlok: assets/csv/scoreboard_clean.csv, highscore.json

Használat:
    python run_stats.py
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
        legjobb="max",
        jatekok_szama="count"
    )
    
    # Kerekítés az átlagnál és mediánnál
    stats["atlag"] = stats["atlag"].round(1)
    stats["median"] = stats["median"].round(1)
        
    
    # Rendezés legjobb pontszám szerint
    stats = stats.sort_values("legjobb", ascending=False)
    
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
            print(f"   {emoji} {row.player}: {row.legjobb} pont ({row.jatekok_szama} játék)")

def main() -> Optional[None]:
    """Főfüggvény: betöltés és statisztikák készítése."""
    print("🚀 Statisztikák készítése...")
    print("MANUAL TEST - ez tényleg az új kód!")
    
    # Adatok betöltése
    df = load_csv_data()
    json_data = load_json_data()
    
    # Statisztikák számítása
    stats = calculate_player_stats(df)
    
    # Összegzés kiírása
    print_summary(df, json_data, stats)
    
    # **2) Highscore JSON beolvasása és összevetés (javulás)**
    try:
        # Highscore JSON → 'player' / 'legjobb_json' DataFrame
        with open("highscore.json", "r", encoding="utf-8") as f:
            hs = json.load(f)

        players = hs.get("players", {})
        rows = [{"player": name, "legjobb_json": rec.get("best", 0)} for name, rec in players.items()]
        hs_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["player","legjobb_json"])

        # Első mért pont (baseline) CSV-ből: idő szerint rendezve, első pont felvétele
        if "date" in df.columns:
            df_sorted = df.sort_values(["player", "date"])
        else:
            # Ha nincs date oszlop, használjuk az eredeti sorrendet
            df_sorted = df.copy()
            
        elso_eredmenys = (
            df_sorted.groupby("player", as_index=False)["score"]
                     .first()
                     .rename(columns={"score":"elso_eredmeny"})
        )

        # Összefésülés és javulás számítás
        merged = (stats
                  .merge(hs_df, on="player", how="left")
                  .merge(elso_eredmenys, on="player", how="left"))

        merged["referencia_legjobb"] = merged["legjobb_json"].fillna(merged["legjobb"])
        merged["javulas"]    = merged["referencia_legjobb"] - merged["elso_eredmeny"]

        print("\nÖsszevetés és javulás:\n",
            merged[["player","elso_eredmeny","referencia_legjobb","javulas","atlag","median"]])
        
        # **Top N listák mentése**
        TOP_N = 3
        top_javulas = merged.sort_values("javulas", ascending=False).head(TOP_N)
        top_legjobb = merged.sort_values("referencia_legjobb", ascending=False).head(TOP_N)

        # Magyar oszlopnevek a mentéshez
        top_javulas_hu = top_javulas.rename(columns={"player": "jatekos"})
        top_legjobb_hu = top_legjobb.rename(columns={"player": "jatekos"})

        # Könyvtár ellenőrzése és mentés az assets/csv mappába
        import os
        os.makedirs("assets/csv", exist_ok=True)
        
        top_javulas_hu.to_csv("assets/csv/top_javulas.csv", index=False, encoding="utf-8")
        top_legjobb_hu.to_csv("assets/csv/top_legjobb.csv", index=False, encoding="utf-8")

        print("Mentve: assets/csv/top_javulas.csv, assets/csv/top_legjobb.csv")
              
    except FileNotFoundError:
        print("\n❌ highscore.json nem található - javulási analízis kihagyva")
    except Exception as e:
        print(f"\n❌ Hiba a javulási analízis során: {e}")
    
    print(f"\n✅ Statisztikák elkészültek!")

if __name__ == "__main__":
    main()
