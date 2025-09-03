# highscore.py (Space Invaders) - Javított verzió
import json
import os
import datetime
import config as cfg


def load_highscores():
    """Betölti a highscore-t; ha nincs fájl, üres sémát ad vissza."""
    if not os.path.exists(cfg.HIGHSCORE_PATH):
        return {"players": {}}
    try:
        with open(cfg.HIGHSCORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # Ha sérült a fájl, visszatérünk üres sémával
        return {"players": {}}


def save_highscores(data):
    """Elmenti szépen formázva (UTF-8, indent=2)."""
    try:
        with open(cfg.HIGHSCORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Hiba a highscore mentésekor: {e}")


def update_highscore(player_name: str, score: int, level: int = 1, lives_left: int = 0):
    """
    Frissíti a játékos highscore adatait.

    Paraméterek:
        player_name (str): A játékos neve
        score (int): Elért pontszám
        level (int): Elért szint (alapértelmezett: 1)
        lives_left (int): Maradt életek száma (alapértelmezett: 0)
    """
    data = load_highscores()
    players = data.setdefault("players", {})
    rec = players.setdefault(player_name, {
        "best": 0,
        "games_played": 0,
        "history": [],
        "top_runs": []
    })

    # Játszmák száma növelés
    rec["games_played"] = rec.get("games_played", 0) + 1

    # Timestamp generálása (ISO formátum idővel)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Új history bejegyzés
    history_entry = {
        "ts": timestamp,
        "score": int(score),
        "level": int(level),
        "lives_left": int(lives_left)
    }
    rec["history"].append(history_entry)

    # Legjobb pont frissítése
    if score > rec["best"]:
        rec["best"] = int(score)

    # Top futások (csak egyedi pontszámok, max 3 legjobb)
    rec.setdefault("top_runs", [])
    existing_scores = {run["score"] for run in rec["top_runs"]}

    if score not in existing_scores:
        rec["top_runs"].append({"ts": timestamp, "score": int(score)})
        rec["top_runs"] = sorted(rec["top_runs"], key=lambda r: r["score"], reverse=True)[:3]

    save_highscores(data)

    print(
        f"Highscore frissítve: {player_name} - {score} pont "
        f"(szint: {level}, életek: {lives_left}, játszmák: {rec['games_played']})"
    )


def get_player_best(player_name: str) -> int:
    """
    Visszaadja egy játékos legjobb eredményét.
    
    Paraméterek:
        player_name (str): A játékos neve
        
    Visszatérés:
        int: A legjobb pontszám, vagy 0 ha nincs adat
    """
    data = load_highscores()
    players = data.get("players", {})
    player_data = players.get(player_name, {})
    return player_data.get("best", 0)


def get_top_players(limit: int = 5) -> list:
    """
    Visszaadja a legjobb játékosok listáját.
    
    Paraméterek:
        limit (int): Hány játékost adjunk vissza (alapértelmezett: 5)
        
    Visszatérés:
        list: [{"name": str, "best": int}, ...] formátumú lista
    """
    data = load_highscores()
    players = data.get("players", {})
    
    top_list = []
    for name, player_data in players.items():
        top_list.append({
            "name": name,
            "best": player_data.get("best", 0)
        })
    
    # Rendezés pontszám szerint csökkenően
    top_list.sort(key=lambda x: x["best"], reverse=True)
    return top_list[:limit]


def print_highscores():
    """Kiírja a konzolra a top 5 játékost."""
    top = get_top_players(5)
    if not top:
        print("Még nincs highscore adat.")
        return
        
    print("=== TOP 5 HIGHSCORES ===")
    for i, player in enumerate(top, 1):
        print(f"{i}. {player['name']}: {player['best']} pont")
