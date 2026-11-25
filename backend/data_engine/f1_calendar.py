"""
F1 Multi-Season Calendar & Circuit Intelligence Engine
Provides official FIA calendars, driver grids, circuit geometries, and high-frequency
telemetry models for the 2025 and 2026 Formula 1 World Championship seasons.

Only the seasons the dashboard exposes are served; anything else raises ValueError
so unsupported years cannot silently fall through to another season's data.
"""

import math
import numpy as np
from typing import Dict, List, Optional, Any

# ─── Driver Rosters ───────────────────────────────────────────────────────────
# Final 2025 grid (Abu Dhabi, OpenF1 session 9981) and current 2026 grid
# (Las Vegas, OpenF1 session 11420). Numbers, teams and colours are the
# values OpenF1 reports for those sessions; mid-season swaps are captured by
# /api/f1/drivers, which resolves the real entry list per session.

DRIVERS_2025 = [
    {"number": "1",  "code": "VER", "name": "Max Verstappen",        "team": "Red Bull Racing", "color": "#4781D7"},
    {"number": "22", "code": "TSU", "name": "Yuki Tsunoda",          "team": "Red Bull Racing", "color": "#4781D7"},
    {"number": "4",  "code": "NOR", "name": "Lando Norris",          "team": "McLaren",         "color": "#F47600"},
    {"number": "81", "code": "PIA", "name": "Oscar Piastri",         "team": "McLaren",         "color": "#F47600"},
    {"number": "16", "code": "LEC", "name": "Charles Leclerc",       "team": "Ferrari",         "color": "#ED1131"},
    {"number": "44", "code": "HAM", "name": "Lewis Hamilton",        "team": "Ferrari",         "color": "#ED1131"},
    {"number": "63", "code": "RUS", "name": "George Russell",        "team": "Mercedes",        "color": "#00D7B6"},
    {"number": "12", "code": "ANT", "name": "Kimi Antonelli",        "team": "Mercedes",        "color": "#00D7B6"},
    {"number": "14", "code": "ALO", "name": "Fernando Alonso",       "team": "Aston Martin",    "color": "#229971"},
    {"number": "18", "code": "STR", "name": "Lance Stroll",          "team": "Aston Martin",    "color": "#229971"},
    {"number": "55", "code": "SAI", "name": "Carlos Sainz",          "team": "Williams",        "color": "#1868DB"},
    {"number": "23", "code": "ALB", "name": "Alexander Albon",       "team": "Williams",        "color": "#1868DB"},
    {"number": "10", "code": "GAS", "name": "Pierre Gasly",          "team": "Alpine",          "color": "#00A1E8"},
    {"number": "43", "code": "COL", "name": "Franco Colapinto",      "team": "Alpine",          "color": "#00A1E8"},
    {"number": "31", "code": "OCO", "name": "Esteban Ocon",          "team": "Haas F1 Team",    "color": "#9C9FA2"},
    {"number": "87", "code": "BEA", "name": "Oliver Bearman",        "team": "Haas F1 Team",    "color": "#9C9FA2"},
    {"number": "27", "code": "HUL", "name": "Nico Hülkenberg",       "team": "Kick Sauber",     "color": "#01C00E"},
    {"number": "5",  "code": "BOR", "name": "Gabriel Bortoleto",     "team": "Kick Sauber",     "color": "#01C00E"},
    {"number": "30", "code": "LAW", "name": "Liam Lawson",           "team": "Racing Bulls",    "color": "#6C98FF"},
    {"number": "6",  "code": "HAD", "name": "Isack Hadjar",          "team": "Racing Bulls",    "color": "#6C98FF"},
]

DRIVERS_2026 = [
    {"number": "1",  "code": "NOR", "name": "Lando Norris",          "team": "McLaren",         "color": "#F47600"},
    {"number": "81", "code": "PIA", "name": "Oscar Piastri",         "team": "McLaren",         "color": "#F47600"},
    {"number": "16", "code": "LEC", "name": "Charles Leclerc",       "team": "Ferrari",         "color": "#ED1131"},
    {"number": "44", "code": "HAM", "name": "Lewis Hamilton",        "team": "Ferrari",         "color": "#ED1131"},
    {"number": "63", "code": "RUS", "name": "George Russell",        "team": "Mercedes",        "color": "#00D7B6"},
    {"number": "12", "code": "ANT", "name": "Kimi Antonelli",        "team": "Mercedes",        "color": "#00D7B6"},
    {"number": "3",  "code": "VER", "name": "Max Verstappen",        "team": "Red Bull Racing", "color": "#4781D7"},
    {"number": "6",  "code": "HAD", "name": "Isack Hadjar",          "team": "Red Bull Racing", "color": "#4781D7"},
    {"number": "30", "code": "LAW", "name": "Liam Lawson",           "team": "Racing Bulls",    "color": "#6C98FF"},
    {"number": "41", "code": "LIN", "name": "Arvid Lindblad",        "team": "Racing Bulls",    "color": "#6C98FF"},
    {"number": "14", "code": "ALO", "name": "Fernando Alonso",       "team": "Aston Martin",    "color": "#229971"},
    {"number": "18", "code": "STR", "name": "Lance Stroll",          "team": "Aston Martin",    "color": "#229971"},
    {"number": "55", "code": "SAI", "name": "Carlos Sainz",          "team": "Williams",        "color": "#1868DB"},
    {"number": "23", "code": "ALB", "name": "Alexander Albon",       "team": "Williams",        "color": "#1868DB"},
    {"number": "10", "code": "GAS", "name": "Pierre Gasly",          "team": "Alpine",          "color": "#00A1E8"},
    {"number": "43", "code": "COL", "name": "Franco Colapinto",      "team": "Alpine",          "color": "#00A1E8"},
    {"number": "27", "code": "HUL", "name": "Nico Hülkenberg",       "team": "Audi",            "color": "#F50537"},
    {"number": "5",  "code": "BOR", "name": "Gabriel Bortoleto",     "team": "Audi",            "color": "#F50537"},
    {"number": "11", "code": "PER", "name": "Sergio Pérez",          "team": "Cadillac",        "color": "#909090"},
    {"number": "77", "code": "BOT", "name": "Valtteri Bottas",       "team": "Cadillac",        "color": "#909090"},
    {"number": "51", "code": "CAM", "name": "Rafael Camara",         "team": "Haas F1 Team",    "color": "#9C9FA2"},
    {"number": "87", "code": "BEA", "name": "Oliver Bearman",        "team": "Haas F1 Team",    "color": "#9C9FA2"},
]

# ─── 2025 FIA Official Formula 1 World Championship Calendar ───────────────────

CALENDAR_2025 = [
    {"round": 1,  "id": "australia",    "name": "Australian Grand Prix",     "circuit": "Albert Park Circuit",           "country": "Australia",      "location": "Melbourne",         "lap_len": 5.278, "ref_time": 76.5, "corners": 14},
    {"round": 2,  "id": "china",        "name": "Chinese Grand Prix",        "circuit": "Shanghai International Circuit", "country": "China",          "location": "Shanghai",          "lap_len": 5.451, "ref_time": 93.8, "corners": 16},
    {"round": 3,  "id": "japan",        "name": "Japanese Grand Prix",       "circuit": "Suzuka International Racing",   "country": "Japan",          "location": "Suzuka",            "lap_len": 5.807, "ref_time": 88.2, "corners": 18},
    {"round": 4,  "id": "bahrain",      "name": "Bahrain Grand Prix",        "circuit": "Bahrain International Circuit",  "country": "Bahrain",        "location": "Sakhir",            "lap_len": 5.412, "ref_time": 89.1, "corners": 15},
    {"round": 5,  "id": "saudi_arabia", "name": "Saudi Arabian Grand Prix",  "circuit": "Jeddah Corniche Circuit",       "country": "Saudi Arabia",   "location": "Jeddah",            "lap_len": 6.174, "ref_time": 87.4, "corners": 27},
    {"round": 6,  "id": "miami",        "name": "Miami Grand Prix",          "circuit": "Miami International Autodrome",  "country": "United States",  "location": "Miami Gardens",     "lap_len": 5.412, "ref_time": 87.2, "corners": 19},
    {"round": 7,  "id": "imola",        "name": "Emilia Romagna Grand Prix", "circuit": "Autodromo Enzo e Dino Ferrari",  "country": "Italy",          "location": "Imola",             "lap_len": 4.909, "ref_time": 74.8, "corners": 19},
    {"round": 8,  "id": "monaco",       "name": "Monaco Grand Prix",         "circuit": "Circuit de Monaco",             "country": "Monaco",         "location": "Monte Carlo",       "lap_len": 3.337, "ref_time": 71.4, "corners": 19},
    {"round": 9,  "id": "spain",        "name": "Spanish Grand Prix",        "circuit": "Circuit de Barcelona-Catalunya", "country": "Spain",          "location": "Barcelona",         "lap_len": 4.657, "ref_time": 72.3, "corners": 14},
    {"round": 10, "id": "canada",       "name": "Canadian Grand Prix",       "circuit": "Circuit Gilles Villeneuve",     "country": "Canada",         "location": "Montréal",          "lap_len": 4.361, "ref_time": 72.0, "corners": 14},
    {"round": 11, "id": "austria",      "name": "Austrian Grand Prix",       "circuit": "Red Bull Ring",                 "country": "Austria",        "location": "Spielberg",         "lap_len": 4.318, "ref_time": 64.3, "corners": 10},
    {"round": 12, "id": "silverstone",  "name": "British Grand Prix",        "circuit": "Silverstone Circuit",           "country": "United Kingdom", "location": "Silverstone",       "lap_len": 5.891, "ref_time": 85.8, "corners": 18},
    {"round": 13, "id": "spa",          "name": "Belgian Grand Prix",        "circuit": "Circuit de Spa-Francorchamps",  "country": "Belgium",        "location": "Spa-Francorchamps", "lap_len": 7.004, "ref_time": 103.2,"corners": 19},
    {"round": 14, "id": "hungary",      "name": "Hungarian Grand Prix",      "circuit": "Hungaroring",                   "country": "Hungary",        "location": "Budapest",          "lap_len": 4.381, "ref_time": 75.2, "corners": 14},
    {"round": 15, "id": "netherlands",  "name": "Dutch Grand Prix",          "circuit": "Circuit Zandvoort",             "country": "Netherlands",    "location": "Zandvoort",         "lap_len": 4.259, "ref_time": 69.6, "corners": 14},
    {"round": 16, "id": "monza",        "name": "Italian Grand Prix",        "circuit": "Autodromo Nazionale Monza",     "country": "Italy",          "location": "Monza",             "lap_len": 5.793, "ref_time": 79.4, "corners": 11},
    {"round": 17, "id": "baku",         "name": "Azerbaijan Grand Prix",     "circuit": "Baku City Circuit",             "country": "Azerbaijan",     "location": "Baku",              "lap_len": 6.003, "ref_time": 100.3,"corners": 20},
    {"round": 18, "id": "singapore",    "name": "Singapore Grand Prix",      "circuit": "Marina Bay Street Circuit",     "country": "Singapore",      "location": "Marina Bay",        "lap_len": 4.940, "ref_time": 89.5, "corners": 19},
    {"round": 19, "id": "austin",       "name": "United States Grand Prix",  "circuit": "Circuit of The Americas",       "country": "United States",  "location": "Austin",            "lap_len": 5.513, "ref_time": 92.8, "corners": 20},
    {"round": 20, "id": "mexico",       "name": "Mexico City Grand Prix",    "circuit": "Autódromo Hermanos Rodríguez",  "country": "Mexico",         "location": "Mexico City",       "lap_len": 4.304, "ref_time": 77.1, "corners": 17},
    {"round": 21, "id": "brazil",       "name": "São Paulo Grand Prix",      "circuit": "Autódromo de Interlagos",       "country": "Brazil",         "location": "São Paulo",         "lap_len": 4.309, "ref_time": 69.7, "corners": 15},
    {"round": 22, "id": "las_vegas",   "name": "Las Vegas Grand Prix",      "circuit": "Las Vegas Strip Circuit",       "country": "United States",  "location": "Las Vegas",         "lap_len": 6.201, "ref_time": 92.7, "corners": 17},
    {"round": 23, "id": "qatar",       "name": "Qatar Grand Prix",          "circuit": "Lusail International Circuit",  "country": "Qatar",          "location": "Lusail",            "lap_len": 5.419, "ref_time": 80.5, "corners": 16},
    {"round": 24, "id": "abu_dhabi",   "name": "Abu Dhabi Grand Prix",      "circuit": "Yas Marina Circuit",            "country": "UAE",            "location": "Yas Island",        "lap_len": 5.281, "ref_time": 82.2, "corners": 16},
]

# ─── 2026 FIA Formula 1 World Championship Calendar ────────────────────────────
# Rounds 4 (Sakhir) and 5 (Jeddah) were cancelled; the Gulf Air Bahrain Grand
# Prix relocated to Sepang in October, leaving 23 rounds. Venue list measured
# from OpenF1 meetings (2026-11-25). Madrid and Sepang ref_times are the fastest
# 2026 qualifying laps measured from OpenF1 laps.

CALENDAR_2026 = [
    {"round": 1,  "id": "australia",    "name": "Australian Grand Prix",         "circuit": "Albert Park Circuit",           "country": "Australia",      "location": "Melbourne",         "lap_len": 5.278, "ref_time": 75.9, "corners": 14},
    {"round": 2,  "id": "china",        "name": "Chinese Grand Prix",            "circuit": "Shanghai International Circuit", "country": "China",          "location": "Shanghai",          "lap_len": 5.451, "ref_time": 93.1, "corners": 16},
    {"round": 3,  "id": "japan",        "name": "Japanese Grand Prix",           "circuit": "Suzuka International Racing",   "country": "Japan",          "location": "Suzuka",            "lap_len": 5.807, "ref_time": 87.6, "corners": 18},
    {"round": 4,  "id": "miami",        "name": "Miami Grand Prix",              "circuit": "Miami International Autodrome",  "country": "United States",  "location": "Miami Gardens",     "lap_len": 5.412, "ref_time": 86.8, "corners": 19},
    {"round": 5,  "id": "canada",       "name": "Canadian Grand Prix",           "circuit": "Circuit Gilles Villeneuve",     "country": "Canada",         "location": "Montréal",          "lap_len": 4.361, "ref_time": 71.5, "corners": 14},
    {"round": 6,  "id": "monaco",       "name": "Monaco Grand Prix",             "circuit": "Circuit de Monaco",             "country": "Monaco",         "location": "Monte Carlo",       "lap_len": 3.337, "ref_time": 70.9, "corners": 19},
    {"round": 7,  "id": "barcelona",    "name": "Barcelona Grand Prix",          "circuit": "Circuit de Barcelona-Catalunya", "country": "Spain",          "location": "Barcelona",         "lap_len": 4.657, "ref_time": 71.8, "corners": 14},
    {"round": 8,  "id": "austria",      "name": "Austrian Grand Prix",           "circuit": "Red Bull Ring",                 "country": "Austria",        "location": "Spielberg",         "lap_len": 4.318, "ref_time": 63.9, "corners": 10},
    {"round": 9,  "id": "silverstone",  "name": "British Grand Prix",            "circuit": "Silverstone Circuit",           "country": "United Kingdom", "location": "Silverstone",       "lap_len": 5.891, "ref_time": 85.2, "corners": 18},
    {"round": 10, "id": "spa",          "name": "Belgian Grand Prix",            "circuit": "Circuit de Spa-Francorchamps",  "country": "Belgium",        "location": "Spa-Francorchamps", "lap_len": 7.004, "ref_time": 102.6,"corners": 19},
    {"round": 11, "id": "hungary",      "name": "Hungarian Grand Prix",          "circuit": "Hungaroring",                   "country": "Hungary",        "location": "Budapest",          "lap_len": 4.381, "ref_time": 74.8, "corners": 14},
    {"round": 12, "id": "netherlands",  "name": "Dutch Grand Prix",              "circuit": "Circuit Zandvoort",             "country": "Netherlands",    "location": "Zandvoort",         "lap_len": 4.259, "ref_time": 69.1, "corners": 14},
    {"round": 13, "id": "monza",        "name": "Italian Grand Prix",            "circuit": "Autodromo Nazionale Monza",     "country": "Italy",          "location": "Monza",             "lap_len": 5.793, "ref_time": 78.9, "corners": 11},
    {"round": 14, "id": "madrid",       "name": "Spanish Grand Prix",            "circuit": "Madring",                       "country": "Spain",          "location": "Madrid",            "lap_len": 5.474, "ref_time": 91.8, "corners": 20},
    {"round": 15, "id": "baku",         "name": "Azerbaijan Grand Prix",         "circuit": "Baku City Circuit",             "country": "Azerbaijan",     "location": "Baku",              "lap_len": 6.003, "ref_time": 99.8, "corners": 20},
    {"round": 16, "id": "malaysia",     "name": "Bahrain Grand Prix in Malaysia","circuit": "Sepang International Circuit",  "country": "Malaysia",       "location": "Kuala Lumpur",      "lap_len": 5.543, "ref_time": 95.1, "corners": 15},
    {"round": 17, "id": "singapore",    "name": "Singapore Grand Prix",          "circuit": "Marina Bay Street Circuit",     "country": "Singapore",      "location": "Marina Bay",        "lap_len": 4.940, "ref_time": 88.9, "corners": 19},
    {"round": 18, "id": "austin",       "name": "United States Grand Prix",      "circuit": "Circuit of The Americas",       "country": "United States",  "location": "Austin",            "lap_len": 5.513, "ref_time": 92.1, "corners": 20},
    {"round": 19, "id": "mexico",       "name": "Mexico City Grand Prix",        "circuit": "Autódromo Hermanos Rodríguez",  "country": "Mexico",         "location": "Mexico City",       "lap_len": 4.304, "ref_time": 76.5, "corners": 17},
    {"round": 20, "id": "brazil",       "name": "São Paulo Grand Prix",          "circuit": "Autódromo de Interlagos",       "country": "Brazil",         "location": "São Paulo",         "lap_len": 4.309, "ref_time": 69.2, "corners": 15},
    {"round": 21, "id": "las_vegas",    "name": "Las Vegas Grand Prix",          "circuit": "Las Vegas Strip Circuit",       "country": "United States",  "location": "Las Vegas",         "lap_len": 6.201, "ref_time": 91.9, "corners": 17},
    {"round": 22, "id": "qatar",        "name": "Qatar Grand Prix",              "circuit": "Lusail International Circuit",  "country": "Qatar",          "location": "Lusail",            "lap_len": 5.419, "ref_time": 79.9, "corners": 16},
    {"round": 23, "id": "abu_dhabi",    "name": "Abu Dhabi Grand Prix",          "circuit": "Yas Marina Circuit",            "country": "UAE",            "location": "Yas Island",        "lap_len": 5.281, "ref_time": 81.6, "corners": 16},
]

# ─── Geometric Circuit Coordinates for Dynamic Track Maps ─────────────────────

from backend.data_engine.circuit_geometries import (
    CIRCUIT_TEMPLATES,
    generate_track_geometry,
    get_circuit_template
)

# ─── High-Level Calendar Accessors ───────────────────────────────────────────

def get_seasons() -> List[int]:
    """Returns the F1 Championship seasons the dashboard serves."""
    return [2026, 2025]

def _require_supported(year: int) -> None:
    if year not in (2025, 2026):
        raise ValueError(f"Season {year} is not available; supported seasons: 2025, 2026.")

def get_season_calendar(year: int) -> List[Dict[str, Any]]:
    """Returns official FIA calendar for the requested season."""
    _require_supported(year)
    return CALENDAR_2026 if year == 2026 else CALENDAR_2025

def get_season_drivers(year: int) -> List[Dict[str, Any]]:
    """Returns the season's final/current entry list with car numbers and liveries."""
    _require_supported(year)
    return DRIVERS_2026 if year == 2026 else DRIVERS_2025

def get_event_meta(year: int, event_identifier: str) -> Dict[str, Any]:
    """Finds Grand Prix metadata by ID, alias, or name substring."""
    cal = get_season_calendar(year)
    clean_id = event_identifier.lower().replace("-", "_").replace(" ", "_")
    
    # 1. Exact ID match
    for ev in cal:
        if ev["id"] == clean_id:
            return ev
            
    # 2. Alias mapping
    alias_map = {
        "usa": "austin",
        "cota": "austin",
        "texas": "austin",
        "united_states": "austin",
        "emilia_romagna": "imola",
        "azerbaijan": "baku",
        "great_britain": "silverstone",
        "britain": "silverstone",
        "italy": "monza",
        "belgium": "spa",
        "monte_carlo": "monaco",
        "melbourne": "australia",
        "albert_park": "australia",
        "sao_paulo": "brazil",
        "interlagos": "brazil",
        "suzuka": "japan",
        "spielberg": "austria",
        "red_bull_ring": "austria",
        "zandvoort": "netherlands",
        "sakhir": "bahrain",
        "jeddah": "saudi_arabia",
        "shanghai": "china",
        "budapest": "hungary",
        "hungaroring": "hungary",
        "barcelona": "barcelona",
        "catalunya": "barcelona",
        "malaysia": "malaysia",
        "sepang": "malaysia",
        "kuala_lumpur": "malaysia",
        "madrid": "madrid",
        "madring": "madrid",
        "mexico_city": "mexico",
        "vegas": "las_vegas",
        "lusail": "qatar",
        "yas_marina": "abu_dhabi"
    }
    if clean_id in alias_map:
        target_id = alias_map[clean_id]
        for ev in cal:
            if ev["id"] == target_id:
                return ev

    # 2025 calls the Barcelona round "spain"; the 2026 calendar renames it.
    if clean_id in ("barcelona", "catalunya"):
        for ev in cal:
            if ev["id"] == "spain":
                return ev

    # 3. Substring match
    for ev in cal:
        if clean_id in ev["id"] or clean_id in ev["name"].lower().replace(" ", "_") or clean_id in ev.get("country", "").lower():
            return ev
            
    return cal[0]

# Per-circuit sector time ratios (s1%, s2%, s3%) based on official F1 sector definitions.
# These replace the previous flat 31/38/31 split applied to every circuit.
CIRCUIT_SECTOR_RATIOS: Dict[str, tuple] = {
    "monaco":       (0.42, 0.22, 0.36),
    "spa":          (0.29, 0.39, 0.32),
    "monza":        (0.29, 0.39, 0.32),
    "silverstone":  (0.33, 0.37, 0.30),
    "suzuka":       (0.35, 0.33, 0.32),
    "australia":    (0.32, 0.36, 0.32),
    "bahrain":      (0.33, 0.35, 0.32),
    "saudi_arabia": (0.30, 0.38, 0.32),
    "china":        (0.32, 0.37, 0.31),
    "miami":        (0.34, 0.35, 0.31),
    "imola":        (0.36, 0.34, 0.30),
    "spain":        (0.33, 0.37, 0.30),
    "barcelona":    (0.33, 0.37, 0.30),
    "madrid":       (0.31, 0.36, 0.33),
    "malaysia":     (0.26, 0.33, 0.41),
    "canada":       (0.34, 0.35, 0.31),
    "austria":      (0.34, 0.33, 0.33),
    "hungary":      (0.37, 0.35, 0.28),
    "netherlands":  (0.34, 0.35, 0.31),
    "baku":         (0.33, 0.35, 0.32),
    "singapore":    (0.35, 0.34, 0.31),
    "austin":       (0.32, 0.37, 0.31),
    "mexico":       (0.34, 0.36, 0.30),
    "brazil":       (0.35, 0.34, 0.31),
    "las_vegas":    (0.32, 0.37, 0.31),
    "qatar":        (0.33, 0.37, 0.30),
    "abu_dhabi":    (0.34, 0.35, 0.31),
    "japan":        (0.35, 0.33, 0.32),
}


def _sector_ratios(circuit_id: str) -> tuple:
    """Returns (s1_ratio, s2_ratio, s3_ratio) for the given circuit, or the default 31/38/31 split."""
    return CIRCUIT_SECTOR_RATIOS.get(circuit_id, (0.31, 0.38, 0.31))


def _simulate_race_laps(ref_time: float, delta_offset: float, total_laps: int, circuit_id: str = "") -> List[Dict[str, Any]]:
    pit_lap = max(5, int(total_laps * 0.38))
    laps = []
    best_time = 999.0
    best_lap = 1
    r1, r2, _ = _sector_ratios(circuit_id)
    
    for l in range(1, total_laps + 1):
        fuel_penalty = 3.2 * (1.0 - (l - 1) / float(total_laps))
        if l <= pit_lap:
            compound = "MEDIUM"
            stint = 1
            stint_lap = l
            tire_deg = (stint_lap ** 1.1) * 0.05
        else:
            compound = "HARD"
            stint = 2
            stint_lap = l - pit_lap
            tire_deg = (stint_lap ** 1.05) * 0.038
            
        base = ref_time + delta_offset + 2.4
        lap_t = round(float(base + fuel_penalty + tire_deg + np.sin(l * 0.7) * 0.15), 3)
        pit = False
        
        if l == 1:
            lap_t = round(lap_t + 4.5, 3) # Standing start
        elif l == pit_lap:
            lap_t = round(lap_t + 3.2, 3) # Pit In lap
            pit = True
        elif l == pit_lap + 1:
            lap_t = round(lap_t + 18.0, 3) # Pit Out lap + transit
            pit = True
            
        if not pit and l > 1 and lap_t < best_time:
            best_time = lap_t
            best_lap = l
            
        s1 = round(lap_t * r1, 3)
        s2 = round(lap_t * r2, 3)
        s3 = round(lap_t - s1 - s2, 3)
        
        laps.append({
            "lap_number": l,
            "lap_time": lap_t,
            "compound": compound,
            "stint": stint,
            "pit": pit,
            "s1": s1,
            "s2": s2,
            "s3": s3
        })
        
    for item in laps:
        item["is_fastest"] = (item["lap_number"] == best_lap)
        
    return laps

def _simulate_qualifying_laps(ref_time: float, delta_offset: float, circuit_id: str = "") -> List[Dict[str, Any]]:
    # Authentic 20-lap qualifying session (Q1, Q2, Q3 runs)
    structure = [
        # Q1 Run 1
        {"type": "out",  "delta": 35.0, "pit": False, "comp": "SOFT", "stint": 1},
        {"type": "fly",  "delta": 0.85, "pit": False, "comp": "SOFT", "stint": 1},
        {"type": "in",   "delta": 22.0, "pit": True,  "comp": "SOFT", "stint": 1},
        # Q1 Run 2
        {"type": "out",  "delta": 32.0, "pit": False, "comp": "SOFT", "stint": 2},
        {"type": "fly",  "delta": 0.52, "pit": False, "comp": "SOFT", "stint": 2},
        {"type": "in",   "delta": 24.0, "pit": True,  "comp": "SOFT", "stint": 2},
        # Q2 Run 1
        {"type": "out",  "delta": 34.0, "pit": False, "comp": "SOFT", "stint": 3},
        {"type": "fly",  "delta": 0.30, "pit": False, "comp": "SOFT", "stint": 3},
        {"type": "in",   "delta": 23.0, "pit": True,  "comp": "SOFT", "stint": 3},
        # Q2 Run 2
        {"type": "out",  "delta": 33.0, "pit": False, "comp": "SOFT", "stint": 4},
        {"type": "fly",  "delta": 0.15, "pit": False, "comp": "SOFT", "stint": 4},
        {"type": "in",   "delta": 25.0, "pit": True,  "comp": "SOFT", "stint": 4},
        # Q3 Pole Shootout Run 1
        {"type": "out",  "delta": 35.0, "pit": False, "comp": "SOFT", "stint": 5},
        {"type": "fly",  "delta": 0.08, "pit": False, "comp": "SOFT", "stint": 5},
        {"type": "in",   "delta": 22.0, "pit": True,  "comp": "SOFT", "stint": 5},
        # Q3 Pole Shootout Run 2 (Pole Flyer!)
        {"type": "out",  "delta": 34.0, "pit": False, "comp": "SOFT", "stint": 6},
        {"type": "fly",  "delta": 0.00, "pit": False, "comp": "SOFT", "stint": 6},
        {"type": "in",   "delta": 30.0, "pit": True,  "comp": "SOFT", "stint": 6},
    ]
    
    laps = []
    base = ref_time + delta_offset
    best_time = 999.0
    best_lap = 14
    r1, r2, _ = _sector_ratios(circuit_id)
    
    for idx, item in enumerate(structure, start=1):
        lap_t = round(float(base + item["delta"]), 3)
        if item["type"] == "fly" and lap_t < best_time:
            best_time = lap_t
            best_lap = idx
            
        s1 = round(lap_t * r1, 3)
        s2 = round(lap_t * r2, 3)
        s3 = round(lap_t - s1 - s2, 3)
        laps.append({
            "lap_number": idx,
            "lap_time": lap_t,
            "compound": item["comp"],
            "stint": item["stint"],
            "pit": item["pit"],
            "s1": s1,
            "s2": s2,
            "s3": s3
        })
        
    for item in laps:
        item["is_fastest"] = (item["lap_number"] == best_lap)
        
    return laps

def generate_f1_session_telemetry(
    year: int,
    event_id: str,
    session_type: str = "Q",
    driver_number: str = "1",
    lap_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generates 100Hz continuous telemetry arrays matching uPlot schema for any 2025/2026 session.
    Physics-grounded in F1 hybrid powertrain performance (350+ km/h top speeds, 5.5G braking).
    Supports multi-lap race stint progression and per-lap telemetry extraction.
    """
    ev_meta = get_event_meta(year, event_id)
    lap_time = ev_meta.get("ref_time", 76.5)
    
    # Retrieve driver details (match by car number or 3-letter driver code)
    drivers = get_season_drivers(year)
    clean_driver = str(driver_number).strip().upper()
    driver_obj = next((d for d in drivers if str(d["number"]) == clean_driver or d["code"].upper() == clean_driver), drivers[0])
    
    # Slight driver performance delta
    delta_offset = 0.0
    if driver_obj["team"] in ["Red Bull Racing", "McLaren", "Ferrari"]:
        delta_offset = -0.4
    elif driver_obj["team"] in ["Mercedes", "Aston Martin"]:
        delta_offset = 0.2
    else:
        delta_offset = 0.8

    # Deterministic per-driver variation: the team tier alone made teammates
    # render byte-identical traces (every Red Bull/Ferrari driver shared -0.4).
    rng = np.random.default_rng(int(driver_obj["number"]) * 7919 + int(year))
    delta_offset += float(np.round(rng.uniform(-0.12, 0.12), 3))
    speed_scale = 1.0 + float(rng.uniform(-0.012, 0.012))
    brake_scale = float(rng.uniform(0.94, 1.06))
        
    # Calculate total laps and full stint progression
    total_laps = 78 if ev_meta["id"] == "monaco" else int(np.ceil(305.0 / ev_meta.get("lap_len", 5.2)))
    
    if session_type.upper() == "R":
        laps_summary = _simulate_race_laps(lap_time, delta_offset, total_laps, circuit_id=ev_meta["id"])
    else:
        laps_summary = _simulate_qualifying_laps(lap_time, delta_offset, circuit_id=ev_meta["id"])
        total_laps = len(laps_summary)

    # Resolve active lap
    fastest_lap_obj = next((l for l in laps_summary if l.get("is_fastest")), laps_summary[0])
    if lap_number is not None and int(lap_number) > 0:
        active_lap = next((l for l in laps_summary if l["lap_number"] == int(lap_number)), fastest_lap_obj)
    else:
        active_lap = fastest_lap_obj

    total_time = round(float(active_lap["lap_time"]), 3)
    hz = 100
    n_samples = int(total_time * hz)
    times = [round(t, 3) for t in np.linspace(0.0, total_time, n_samples)]
    
    track_map = generate_track_geometry(ev_meta["id"], total_time)
    corners = track_map["corner_pins"]
    
    # Synthesize Speed, Throttle, Brake profiles aligned with corner pins
    speeds = np.zeros(n_samples)
    throttles = np.zeros(n_samples, dtype=int)
    brakes = np.zeros(n_samples, dtype=int)
    gears = np.zeros(n_samples, dtype=int)
    rpms = np.zeros(n_samples, dtype=int)
    
    # Pit-lane speed limiting if active lap is pit in/out
    is_pit_lap = active_lap.get("pit", False)
    pit_speed_limit = 60.0 if ev_meta["id"] == "monaco" else 80.0
    current_speed = pit_speed_limit if is_pit_lap and active_lap["lap_number"] > 1 else 280.0
    
    # Mark braking zones based on corners
    braking_mask = np.zeros(n_samples, dtype=bool)
    for c in corners:
        start_idx = int((c["start"] / total_time) * n_samples)
        end_idx = int((c["end"] / total_time) * n_samples)
        braking_mask[start_idx:end_idx] = True
        
    for i in range(n_samples):
        # Apply pit limiter on final 20% or initial 20% of pit lap
        if is_pit_lap and (i > int(n_samples * 0.8) or i < int(n_samples * 0.2)):
            current_speed = pit_speed_limit
            speeds[i] = round(current_speed, 1)  # was missing — caused 0 km/h in pit segment
            throttles[i] = 40
            brakes[i] = 0
            gears[i] = 2
            rpms[i] = 6200
        elif braking_mask[i]:
            current_speed = max(65.0, current_speed - 4.2)
            throttles[i] = 0
            brakes[i] = min(100, int(brakes[max(0, i-1)] + 18)) if current_speed > 90 else 30
            speeds[i] = round(current_speed, 1)
            gears[i] = 2 if current_speed < 85 else (3 if current_speed < 140 else 4)
            rpms[i] = int(9500 + current_speed * 20)
        else:
            current_speed = min(342.0, current_speed + 1.6)
            throttles[i] = min(100, int(throttles[max(0, i-1)] + 8))
            brakes[i] = 0
            speeds[i] = round(current_speed, 1)
            
            # Gear and RPM heuristics
            if current_speed < 85:
                gears[i] = 2
                rpms[i] = int(9500 + current_speed * 30)
            elif current_speed < 140:
                gears[i] = 3
                rpms[i] = int(9800 + current_speed * 20)
            elif current_speed < 195:
                gears[i] = 4
                rpms[i] = int(10200 + current_speed * 15)
            elif current_speed < 245:
                gears[i] = 5
                rpms[i] = int(10500 + current_speed * 10)
            elif current_speed < 290:
                gears[i] = 6
                rpms[i] = int(10800 + current_speed * 8)
            elif current_speed < 320:
                gears[i] = 7
                rpms[i] = int(11200 + current_speed * 5)
            else:
                gears[i] = 8
                rpms[i] = int(11500 + (current_speed - 320) * 12)

    s1_time = active_lap.get("s1", round(total_time * 0.31, 3))
    s2_time = active_lap.get("s2", round(total_time * 0.38, 3))

    # Per-driver shaping of the synthetic profile (deterministic, seed above).
    speeds = np.round(np.clip(speeds * speed_scale, 0.0, 342.0), 1)
    brakes = np.clip(np.rint(brakes * brake_scale).astype(int), 0, 100)

    return {
        "status": "success",
        "simulated": True,
        "session_id": f"{year}_{ev_meta['id']}_{session_type}",
        "driver": str(driver_obj["number"]),
        "driver_name": driver_obj["name"],
        "driver_code": driver_obj["code"],
        "team_name": driver_obj["team"],
        "team_color": driver_obj["color"],
        "lap_number": int(active_lap["lap_number"]),
        "total_laps": total_laps,
        "lap_time_seconds": total_time,
        "compound": active_lap.get("compound", "MEDIUM"),
        "is_fastest_lap": active_lap.get("is_fastest", False),
        "circuit_name": ev_meta["circuit"],
        "event_name": ev_meta["name"],
        "country": ev_meta["country"],
        "lap_len": track_map.get("lap_len", f"{ev_meta.get('lap_len', 5.2)} km"),
        "sectors": {
            "s1_end": s1_time,
            "s2_end": round(s1_time + s2_time, 3),
            "total_time": total_time
        },
        "corners": corners,
        "track_map": track_map,
        "laps_summary": laps_summary,
        "channels": ["Time (s)", "Speed (km/h)", "Throttle (%)", "Brake (%)", "Gear", "RPM"],
        "series": [times, speeds.tolist(), throttles.tolist(), brakes.tolist(), gears.tolist(), rpms.tolist()]
    }
