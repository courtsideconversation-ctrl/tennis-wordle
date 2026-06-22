"""
fetch_player_stats.py
---------------------
Fetches detailed stats for the ATP top 100 and writes player_stats.json.

Run:  set RAPIDAPI_KEY=your_key && python scripts/fetch_player_stats.py
"""

import os, json, time, pathlib, requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
if not RAPIDAPI_KEY:
    raise SystemExit("ERROR: RAPIDAPI_KEY env var is not set.")

BASE_URL = "https://tennis-api-atp-wta-itf.p.rapidapi.com"
HEADERS  = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com",
}

REPO_ROOT = pathlib.Path(__file__).parent.parent
OUTPUT    = REPO_ROOT / "data" / "player_stats.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

CONTINENT_MAP = {
    "SRB":"Europe","ESP":"Europe","GER":"Europe","RUS":"Europe","NOR":"Europe",
    "GRE":"Europe","GBR":"Europe","FRA":"Europe","ITA":"Europe","SUI":"Europe",
    "AUT":"Europe","CRO":"Europe","POL":"Europe","BEL":"Europe","NED":"Europe",
    "SVK":"Europe","CZE":"Europe","HUN":"Europe","BUL":"Europe","SWE":"Europe",
    "DEN":"Europe","FIN":"Europe","POR":"Europe","ROM":"Europe","UKR":"Europe",
    "MNE":"Europe","BIH":"Europe","SVN":"Europe","LUX":"Europe","MON":"Europe",
    "GEO":"Europe","LAT":"Europe","EST":"Europe","LTU":"Europe","MKD":"Europe",
    "ALB":"Europe","ARM":"Europe","AZE":"Europe","BLR":"Europe",
    "USA":"Americas","ARG":"Americas","CAN":"Americas","BRA":"Americas","CHI":"Americas",
    "COL":"Americas","PER":"Americas","URU":"Americas","ECU":"Americas",
    "PAR":"Americas","VEN":"Americas","MEX":"Americas","DOM":"Americas",
    "AUS":"Oceania","NZL":"Oceania",
    "JPN":"Asia","CHN":"Asia","KOR":"Asia","IND":"Asia","TPE":"Asia",
    "KAZ":"Asia","UZB":"Asia","INA":"Asia","PHI":"Asia","MAS":"Asia",
    "ISR":"Asia","JOR":"Asia","LIB":"Asia",
    "RSA":"Africa","MAR":"Africa","EGY":"Africa","TUN":"Africa","ZIM":"Africa",
}

def get(path, params=None):
    resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data

def get_rankings():
    raw = get("/tennis/v2/atp/ranking/singles", params={"pageSize": 100, "pageNo": 1})
    return raw[:100]

def get_profile(pid):
    try:
        return get(f"/tennis/v2/atp/player/profile/{pid}") or {}
    except Exception:
        return {}

def get_surface_summary(pid):
    try:
        data = get(f"/tennis/v2/atp/player/surface-summary/{pid}")
        if not data: return "Unknown"
        totals = {}
        for year_entry in data:
            for s in year_entry.get("surfaces", []):
                court = s.get("court", "")
                if not court: continue
                # Normalize surface names
                if "hard" in court.lower() and "indoor" not in court.lower():
                    court = "Hard"
                elif "clay" in court.lower():
                    court = "Clay"
                elif "grass" in court.lower():
                    court = "Grass"
                else:
                    continue
                w = int(s.get("courtWins", 0) or 0)
                l = int(s.get("courtLosses", 0) or 0)
                if court not in totals:
                    totals[court] = [0, 0]
                totals[court][0] += w
                totals[court][1] += l
        best, best_rate = "Unknown", -1
        for court, (w, l) in totals.items():
            if w + l < 10: continue
            rate = w / (w + l)
            if rate > best_rate:
                best_rate = rate
                best = court
        return best
    except Exception:
        return "Unknown"

def get_titles(pid):
    """Returns (grand_slam_titles, total_main_tour_titles)"""
    try:
        data = get(f"/tennis/v2/atp/player/titles/{pid}")
        if not data: return 0, 0
        gs_titles    = 0
        total_titles = 0
        for entry in data:
            tier_id = entry.get("tourRankId")
            won     = int(entry.get("titlesWon", 0) or 0)
            if tier_id == 4:  # Grand Slam
                gs_titles = won
            if tier_id in (2, 3, 4, 7):  # Main tour + Masters + GS + Tour Finals
                total_titles += won
        return gs_titles, total_titles
    except Exception:
        return 0, 0

def parse_plays(plays_str):
    """Parse 'Right-Handed, Two-Handed Backhand' into (handedness, backhand)"""
    if not plays_str:
        return "Unknown", "Unknown"
    s = plays_str.lower()
    hand = "Left" if "left" in s else ("Right" if "right" in s else "Unknown")
    backhand = "Two-Handed" if "two" in s else ("One-Handed" if "one" in s else "Unknown")
    return hand, backhand

# ── Main ──────────────────────────────────────────────────────────────────────

print("Fetching ATP top 100 rankings...")
rankings = get_rankings()
print(f"Got {len(rankings)} players.\n")

results = []

for i, entry in enumerate(rankings, 1):
    p       = entry["player"]
    pid     = p["id"]
    name    = p["name"]
    rank    = entry.get("position", i)
    country = p.get("countryAcr", "")

    print(f"[{i:3}/100] #{rank} {name}")

    profile = get_profile(pid)
    time.sleep(0.4)

    # Top-level profile fields
    birthday = profile.get("birthday", "") or ""
    birth_year = None
    if birthday:
        try: birth_year = int(birthday[:4])
        except: pass

    ch = profile.get("currentRank")  # sometimes ch is here, check information too
    # Career high is separate — try ch field
    career_high = profile.get("ch") or None
    if career_high:
        try: career_high = int(career_high)
        except: career_high = None

    # information sub-object has the good stuff
    info = profile.get("information") or {}

    height = None
    raw_h  = info.get("height") or profile.get("height")
    if raw_h:
        try: height = int(str(raw_h).replace("cm","").strip())
        except: pass

    turned_pro = None
    tp = info.get("turnedPro") or info.get("turned_pro") or ""
    if tp:
        try: turned_pro = int(str(tp)[:4])
        except: pass

    plays_str = info.get("plays", "") or ""
    handedness, backhand = parse_plays(plays_str)

    # Surface summary
    best_surface = get_surface_summary(pid)
    time.sleep(0.4)

    # Titles
    gs_titles, total_titles = get_titles(pid)
    time.sleep(0.4)

    continent = CONTINENT_MAP.get(country, "Unknown")

    player_data = {
        "id":          pid,
        "name":        name,
        "country":     country,
        "continent":   continent,
        "rank":        rank,
        "careerHigh":  career_high,
        "birthYear":   birth_year,
        "turnedPro":   turned_pro,
        "height":      height,
        "handedness":  handedness,
        "backhand":    backhand,
        "bestSurface": best_surface,
        "grandSlams":  gs_titles,
        "titles":      total_titles,
    }
    results.append(player_data)
    print(f"  ✓ ch={career_high} born={birth_year} pro={turned_pro} h={height} {handedness}/{backhand} surf={best_surface} slams={gs_titles} titles={total_titles}")

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nDone. Wrote {len(results)} players to {OUTPUT}")
