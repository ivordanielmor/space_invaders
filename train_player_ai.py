from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
import joblib
import csv
from typing import List, Tuple
import sys
from pathlib import Path

def train_player_ai(csv_path: str = "examples.csv", model_path: str = "player_model.joblib") -> Tuple[float, int]:
    """Betanít egy K-közeli szomszédok (KNN) modellt az examples.csv alapján, és elmenti.

    Paraméterek:
        csv_path (str): Az adatokat tartalmazó CSV fájl elérési útja (alapértelmezett: "examples.csv").
        model_path (str): A kimeneti modell fájl elérési útja (alapértelmezett: "player_model.joblib").

    Visszatérés:
        Tuple[float, int]: (pontosság, minták száma)
            - pontosság (float): A modell pontossága a tesztadatokon (0.0 és 1.0 között).
            - minták száma (int): A tanító és teszt adatok teljes száma.

    Mellékhatás:
        - A betanított modell a megadott `model_path`-ra mentődik.
        - A konzolra kiíródik a modell pontossága és a mentés megerősítése.
        - Hiba esetén (pl. üres CSV, hiányzó fejléc) a program kilép hibaüzenettel.

    Kivétel dobása:
        FileNotFoundError: Ha a `csv_path` nem létezik.
        ValueError: Ha a CSV üres vagy hiányzik a szükséges fejléc.
    """
    # Adatok betöltése
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"A {csv_path} fájl nem létezik.")

    X: List[List[float]] = []
    y: List[int] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        # Ellenőrizzük a fejlécet
        if not all(field in r.fieldnames for field in ["dx", "dy", "action"]):
            raise ValueError("A CSV-nek tartalmaznia kell a 'dx', 'dy', 'action' oszlopokat.")
        
        for row in r:
            X.append([float(row["dx"]), float(row["dy"])])
            y.append(int(row["action"]))

    if not X:
        raise ValueError(f"A {csv_path} üres, nincs adat a tanításhoz.")

    # Adatok felosztása
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Modell tanítása
    model = KNeighborsClassifier(n_neighbors=3)
    model.fit(X_train, y_train)

    # Pontosság kiértékelése
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
    print(f"Pontosság: {round(acc * 100, 1)}%")

    # Modell mentése
    joblib.dump(model, model_path)
    print(f"Mentve: {model_path}")

    return acc, len(X)

if __name__ == "__main__":
    try:
        accuracy, sample_count = train_player_ai()
        print(f"Tanító és teszt minták száma: {sample_count}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Hiba: {e}")
        sys.exit(1)