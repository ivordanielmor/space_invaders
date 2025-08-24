# Space Invaders – Pygame + Hybrid/ML AI

A modern Space Invaders-style game using [Pygame](https://www.pygame.org/news), ⭐ power-ups and two AI modes: **Hybrid** (rules + ML) and **Pure ML** (KNN trained from your own gameplay).

---

## 🕹️ Gameplay

- **Move (manual):** ← / →  
- **Shoot:** Space  
- **Toggle AI on/off:** `M`  
- **Menu:** ↑ / ↓ to navigate, **Enter** to select, **Esc** to quit  
- **Power-up:** ⭐ appears randomly; picking or hitting it grants rapid fire for a few seconds  
- **Lose a life:** on collision **or** when an enemy breaches the player’s row  
- **Game Over:** when lives reach 0  
- **Difficulty:** Easy / Normal / Hard (in the main menu)

---

## 🛠️ Installation & Running

### Requirements
- Python 3.10+
- [Pygame](https://www.pygame.org/news)
- scikit-learn (`sklearn`) + joblib

Install:
```bash
pip install pygame scikit-learn joblib
```

> On Windows, consider a venv:  
> `python -m venv .venv && .venv\Scriptsctivate`

### Run the game
```bash
python main.py
```

---

## 🧠 Train the Player AI (KNN)

During **manual play** (AI off), the game logs examples to `examples.csv` when you press:
- ←  →  (actions 0 / 1)
- Space (action 2)

Columns: `dx, dy, action, speed_multiplier, enemy_count`  
(The trainer uses `dx, dy, action`.)

Train and save the model:
```bash
# Option A: module
python -m train.player.ai

# Option B: direct path
python train/player/ai.py
```

Output:
- Prints test accuracy and sample count
- Saves `player_model.joblib` (auto-loaded by `main.py`)

---

## 🤖 AI Modes & Benchmark

- **Hybrid:**  
  1) ⭐ priority (align horizontally, shoot when centered & off cooldown)  
  2) Enemy aiming: first align horizontally (tight tolerance for small enemies), then shoot  
  3) Respects shooting cooldown and falls back to rule-based logic if needed

- **Pure ML:**  
  Uses the KNN prediction (0=left, 1=right, 2=shoot), with basic cooldown checks.

### 3–3 minute comparison (Hybrid vs ML)
Built-in measurement alternates **Hybrid** and **ML** in 3-minute blocks. **Each switch fully resets** to a clean start at level 1. At the end of a block—or earlier if you lose—**the console prints** the score for that mode and the running summary, e.g.:
```
=== 3 perces blokk vége ===
Mód:  HYBRID  | Score:  1860  | Lives:  2
Összesített eredmények: {'hybrid': 1860, 'ml': 1880}
```

---

## 📷 Screenshot

*(Add your own image)*  
`![Screenshot](./images/screenshot.png)`

---

## 📄 License

This project is intended for learning purposes.

---

# Space Invaders – Pygame + Hibrid/ML AI (Magyar)

Modern **Space Invaders**-jellegű játék [Pygame](https://www.pygame.org/news)-gel, ⭐ power-uppal és két AI-móddal: **Hibrid** (szabályok + ML) és **Tiszta ML** (KNN a saját játékmintáidból).

---

## 🕹️ Játékmenet

- **Mozgás (manuális):** bal/jobb nyíl  
- **Lövés:** Space  
- **AI mód váltása:** `M`  
- **Menü:** fel/le nyíl, **Enter** választ, **Esc** kilép  
- **Power-up:** ⭐ – rövid ideig gyorslövés  
- **Életvesztés:** ütközéskor **vagy** ha az ellenség eléri a játékos sorát  
- **Game Over:** ha elfogynak az életek  
- **Nehézség:** Könnyű / Normál / Nehéz

---

## 🛠️ Telepítés és futtatás

### Követelmények
- Python 3.10+
- Pygame
- scikit-learn + joblib

Telepítés:
```bash
pip install pygame scikit-learn joblib
```

### A játék futtatása
```bash
python main.py
```

---

## 🧠 AI tanítás (KNN)

**Manuális** módban a játék **naplózza** a példákat: `examples.csv` (←=0, →=1, Space=2).  
Oszlopok: `dx, dy, action, speed_multiplier, enemy_count`.

Tréning:
```bash
python -m train.player.ai
# vagy
python train/player/ai.py
```

Eredmény: teszt pontosság, mintaszám, mentett `player_model.joblib` (futáskor automatikusan betöltődik).

---

## 🤖 AI módok & mérés

- **Hibrid:** ⭐ prioritás, vízszintes igazítás kicsi ellenségekre is pontosabban, csak utána lövés; cooldown figyelembevétele; szükség esetén szabály-alapú fallback.
- **Tiszta ML:** KNN (0=balra, 1=jobbra, 2=lő) alapú döntés, minimális szabályozással.

### 3–3 perces összehasonlítás
A beépített mérőmód 3 perc **Hibrid**, majd 3 perc **ML** blokkot futtat, **mindkét váltásnál teljes újraindítással**. A blokk végén (vagy korai Game Overnél) **konzolra kiírja** az eredményt és az összesítést.

---

**Jó játékot! 🚀**
