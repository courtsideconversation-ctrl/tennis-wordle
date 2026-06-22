"""
fetch_player_stats.py
---------------------
Fetches detailed stats for ATP top 100 and writes player_stats.json.
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

def get_with_retry(path, params=None, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=15)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data
        except Exception as e:
            if attempt == retries - 1:
                print(f"  Error after {retries} attempts: {e}")
                return None
            time.sleep(3)
    return None

def get_rankings():
    raw = get_with_retry("/tennis/v2/atp/ranking/singles", params={"pageSize": 100, "pageNo": 1})
    return raw[:100] if raw else []

def get_profile(pid):
    data = get_with_retry(f"/tennis/v2/atp/player/profile/{pid}")
    if isinstance(data, list): return data[0] if data else {}
    return data or {}

def get_titles(pid):
    data = get_with_retry(f"/tennis/v2/atp/player/titles/{pid}")
    if not data: return 0, 0
    gs_titles = 0
    total_titles = 0
    for entry in data:
        tier_id = entry.get("tourRankId")
        won = int(entry.get("titlesWon", 0) or 0)
        if tier_id == 4:
            gs_titles = won
        if tier_id in (2, 3, 4, 7):
            total_titles += won
    return gs_titles, total_titles

def parse_plays(plays_str):
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

    # Career high comes from the ranking entry itself
    career_high = entry.get("ch") or entry.get("careerHigh") or None
    if career_high:
        try: career_high = int(career_high)
        except: career_high = None

    print(f"[{i:3}/100] #{rank} {name}")

    profile = get_profile(pid)
    time.sleep(1.2)  # slower to avoid rate limiting

    birthday = profile.get("birthday", "") or ""
    birth_year = None
    if birthday:
        try: birth_year = int(birthday[:4])
        except: pass

    info = profile.get("information") or {}

    height = None
    raw_h = info.get("height") or profile.get("height")
    if raw_h:
        try: height = int(str(raw_h).replace("cm","").strip())
        except: pass

    turned_pro = None
    tp = info.get("turnedPro") or ""
    if tp:
        try: turned_pro = int(str(tp)[:4])
        except: pass

    plays_str = info.get("plays", "") or ""
    handedness, backhand = parse_plays(plays_str)

    gs_titles, total_titles = get_titles(pid)
    time.sleep(1.2)

    continent = CONTINENT_MAP.get(country, "Unknown")

    player_data = {
        "id":         pid,
        "name":       name,
        "country":    country,
        "continent":  continent,
        "rank":       rank,
        "careerHigh": career_high,
        "birthYear":  birth_year,
        "turnedPro":  turned_pro,
        "height":     height,
        "handedness": handedness,
        "backhand":   backhand,
        "grandSlams": gs_titles,
        "titles":     total_titles,
    }
    results.append(player_data)
    print(f"  ✓ ch={career_high} born={birth_year} pro={turned_pro} h={height} {handedness}/{backhand} slams={gs_titles} titles={total_titles}")

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nDone. Wrote {len(results)} players to {OUTPUT}")
