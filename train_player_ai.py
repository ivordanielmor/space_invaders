"""Space Invaders – játékos AI tréning (KNN).

Feladat:
- Beolvassa a példákat CSV-ből (alap: assets/csv/examples.csv).
- KNeighborsClassifier (k=3) modellt tanít a [dx, dy] → action feladatra.
- Kiértékeli a pontosságot tesztadaton.
- Elmenti a modellt (alap: player_model.joblib).

Elvárt CSV fejléc:
- Kötelező: dx, dy, action
- Opcionális: speed_multiplier, enemy_count (figyelmen kívül hagyjuk)

Használat:
    python train_player_ai.py [CSV_PATH] [MODEL_PATH]

Példák:
    python train_player_ai.py
    python train_player_ai.py assets/csv/examples.csv player_model.joblib
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import csv
import sys
import joblib
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

# --- Alapértelmezett útvonalak (config opcionális) ---
try:
    from config import CSV_DIR as _CFG_CSV_DIR
    DEFAULT_CSV = str(Path(_CFG_CSV_DIR) / "examples.csv")
except Exception:
    DEFAULT_CSV = str(Path("assets") / "csv" / "examples.csv")

DEFAULT_MODEL = "player_model.joblib"


def train_player_ai(csv_path: str = DEFAULT_CSV,
                    model_path: str = DEFAULT_MODEL) -> Tuple[float, int]:
    """KNN modellt tanít az `examples.csv` alapján és elmenti lemezre.

    Paraméterek:
        csv_path (str): Tanító adatok CSV útvonala. Alap: assets/csv/examples.csv.
        model_path (str): A mentendő modell útvonala. Alap: player_model.joblib.

    Visszatérés:
        Tuple[float, int]: (pontosság, összes minta száma)
            - pontosság: a tesztkészlet pontossága 0.0–1.0 között
            - összes minta: betöltött és érvényes sorok száma

    Mellékhatás:
        - Fájlrendszerből olvas és a modellt a `model_path`-ra menti.
        - Konzolra ír információkat (adatok, pontosság, mentési hely).

    Kivétel dobása:
        FileNotFoundError: ha a `csv_path` nem létezik.
        ValueError: ha a CSV üres, vagy hiányzik a 'dx','dy','action' fejléc.

    Példa:
        acc, n = train_player_ai()
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"A fájl nem létezik: {csv_path}")

    X: List[List[float]] = []
    y: List[int] = []
    skipped = 0

    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or not all(h in r.fieldnames for h in ("dx", "dy", "action")):
            raise ValueError("Hiányzó fejléc(ek): szükséges oszlopok: 'dx','dy','action'.")

        for row in r:
            try:
                dx = float(row["dx"]); dy = float(row["dy"]); action = int(row["action"])
                if action not in (0, 1, 2):  # új
                    skipped += 1
                    continue
            except (KeyError, TypeError, ValueError):
                skipped += 1
                continue
            X.append([dx, dy]); y.append(action)

    if not X:
        raise ValueError(f"Üres vagy érvénytelen a CSV: {csv_path}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y  # új: stratify
    )

    model = KNeighborsClassifier(n_neighbors=3)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)

    # modell mentése (szülőkönyvtár létrehozása szükség esetén)
    mp = Path(model_path)
    if mp.parent and str(mp.parent) not in (".", ""):
        mp.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, mp)

    print(f"Minták: összes={len(X)}, kihagyott={skipped}, tanítás={len(X_train)}, teszt={len(X_test)}")
    print(f"Pontosság: {acc:.4f} ({acc*100:.1f}%)")
    print(f"Modell mentve: {model_path}")

    return acc, len(X)


if __name__ == "__main__":
    try:
        cpath = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_CSV
        mpath = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_MODEL
        accuracy, sample_count = train_player_ai(cpath, mpath)
        print(f"Összes minta: {sample_count}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Hiba: {e}")
        sys.exit(1)
