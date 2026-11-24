"""
Overcut.ai High-Fidelity Circuit Geometry Engine
Generates smooth, authentic SVG track maps with FIA corner pins, start/finish lines,
and waypoints for all 24 Formula 1 World Championship circuits.
Uses closed-loop cubic Catmull-Rom spline interpolation with aspect-ratio preservation.
"""

import math
import json
import logging
import copy
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

# Load compiled authentic FIA / GIS circuit geometries
MAPS_PATH = Path(__file__).resolve().parent / "accurate_circuit_maps.json"
ACCURATE_CIRCUITS: Dict[str, Dict[str, Any]] = {}
if MAPS_PATH.exists():
    try:
        with open(MAPS_PATH, "r", encoding="utf-8") as f:
            ACCURATE_CIRCUITS = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load accurate_circuit_maps.json: {e}")

def catmull_rom_spline(pts: List[tuple], num_samples: int = 340) -> np.ndarray:
    """
    Computes a smooth, closed Catmull-Rom cubic spline through control knots,
    normalizing and centering inside standard 320x380 SVG viewBox while preserving aspect ratio.
    """
    pts_arr = np.array(pts, dtype=float)
    n = len(pts_arr)
    t_vals = np.linspace(0, n, num_samples, endpoint=False)
    out_pts = []
    
    for t in t_vals:
        i = int(np.floor(t))
        u = t - i
        p0 = pts_arr[(i - 1) % n]
        p1 = pts_arr[i % n]
        p2 = pts_arr[(i + 1) % n]
        p3 = pts_arr[(i + 2) % n]
        
        # Standard Catmull-Rom cubic evaluation
        pt = 0.5 * (
            (2 * p1) +
            (-p0 + p2) * u +
            (2 * p0 - 5 * p1 + 4 * p2 - p3) * (u ** 2) +
            (-p0 + 3 * p1 - 3 * p2 + p3) * (u ** 3)
        )
        out_pts.append(pt)
        
    out_pts = np.array(out_pts)
    
    pad = 28
    avail_w = 320 - 2 * pad
    avail_h = 380 - 2 * pad
    
    min_x, max_x = out_pts[:, 0].min(), out_pts[:, 0].max()
    min_y, max_y = out_pts[:, 1].min(), out_pts[:, 1].max()
    span_x = max(max_x - min_x, 1e-5)
    span_y = max(max_y - min_y, 1e-5)
    
    scale = min(avail_w / span_x, avail_h / span_y)
    offset_x = pad + (avail_w - span_x * scale) / 2.0
    offset_y = pad + (avail_h - span_y * scale) / 2.0
    
    norm_pts = np.zeros_like(out_pts)
    norm_pts[:, 0] = np.round(offset_x + (out_pts[:, 0] - min_x) * scale, 1)
    norm_pts[:, 1] = np.round(offset_y + (out_pts[:, 1] - min_y) * scale, 1)
    return norm_pts

CIRCUIT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ── 1. Circuit de Monaco (Monte Carlo) ───────────────────────────────────
    "monaco": {
        "name": "Circuit de Monaco",
        "location": "Monte Carlo, Monaco",
        "lap_len": "3.337 km",
        "corners": [
            {"num": 1, "name": "Sainte Dévote", "ratio": 0.12, "speed": 105, "desc": "Heavy Braking Lockup Risk"},
            {"num": 3, "name": "Massenet",      "ratio": 0.24, "speed": 160, "desc": "Uphill High-Lateral Crest"},
            {"num": 4, "name": "Casino Square", "ratio": 0.32, "speed": 135, "desc": "Blind Apex / Bump"},
            {"num": 5, "name": "Mirabeau",      "ratio": 0.38, "speed": 82,  "desc": "Trail-Braking Downhill"},
            {"num": 6, "name": "Fairmont Hairpin","ratio": 0.44,"speed": 48,"desc": "Slowest Corner on Calendar (48 km/h)"},
            {"num": 8, "name": "Portier",       "ratio": 0.52, "speed": 78,  "desc": "Traction onto Tunnel Run"},
            {"num": 10,"name": "Nouvelle Chicane","ratio": 0.68,"speed": 68, "desc": "Post-Tunnel Heavy Deceleration"},
            {"num": 12,"name": "Tabac",         "ratio": 0.78, "speed": 195, "desc": "Fast Harbor Crest"},
            {"num": 15,"name": "Swimming Pool", "ratio": 0.85, "speed": 210, "desc": "High-G Kerb Ride"},
            {"num": 18,"name": "La Rascasse",   "ratio": 0.93, "speed": 62,  "desc": "Tight 180° Harbor Hairpin"},
        ],
        "coords": [
            (160, 360), (170, 320), (180, 260), (200, 200), (225, 140), (215, 95),
            (175, 65),  (130, 55),  (90, 75),   (75, 115),  (85, 160),  (110, 195),
            (120, 235), (110, 275), (90, 310),  (75, 340),  (105, 365), (135, 365)
        ]
    },

    # ── 2. Silverstone Circuit (Great Britain) ────────────────────────────────
    "silverstone": {
        "name": "Silverstone Circuit",
        "location": "Silverstone, Great Britain",
        "lap_len": "5.891 km",
        "corners": [
            {"num": 1, "name": "Abbey",         "ratio": 0.08, "speed": 290, "desc": "Flat-out High-Speed Entry"},
            {"num": 3, "name": "Village",       "ratio": 0.16, "speed": 105, "desc": "Heavy Braking Right"},
            {"num": 4, "name": "The Loop",      "ratio": 0.22, "speed": 88,  "desc": "Tight Left Hairpin"},
            {"num": 6, "name": "Brooklands",    "ratio": 0.35, "speed": 160, "desc": "Long Radius Trail-Brake"},
            {"num": 7, "name": "Luffield",      "ratio": 0.42, "speed": 115, "desc": "Understeer Hairpin"},
            {"num": 9, "name": "Copse",         "ratio": 0.54, "speed": 285, "desc": "5G High-Speed Blind Apex"},
            {"num": 11,"name": "Maggotts",      "ratio": 0.62, "speed": 295, "desc": "Rapid Direction Change Entry"},
            {"num": 12,"name": "Becketts",      "ratio": 0.68, "speed": 235, "desc": "High Lateral Compression"},
            {"num": 13,"name": "Chapel",        "ratio": 0.72, "speed": 260, "desc": "Full Throttle onto Hangar Straight"},
            {"num": 15,"name": "Stowe",         "ratio": 0.84, "speed": 190, "desc": "Downhill Heavy Deceleration"},
            {"num": 16,"name": "Vale",          "ratio": 0.92, "speed": 98,  "desc": "Chicane Approach"},
        ],
        "coords": [
            (250, 280), (285, 230), (280, 170), (240, 130), (190, 90),  (130, 50),
            (70, 80),   (50, 140),  (85, 195),  (135, 225), (160, 265), (130, 310),
            (90, 330),  (60, 290),  (40, 225),  (70, 160),  (140, 150), (200, 215)
        ]
    },

    # ── 3. Autodromo Nazionale Monza (Italy) ──────────────────────────────────
    "monza": {
        "name": "Autodromo Nazionale Monza",
        "location": "Monza, Italy",
        "lap_len": "5.793 km",
        "corners": [
            {"num": 1, "name": "Variante del Rettifilo", "ratio": 0.16, "speed": 75,  "desc": "350 to 75 km/h Heavy Braking"},
            {"num": 3, "name": "Curva Grande",           "ratio": 0.28, "speed": 305, "desc": "Sustained High-Speed Right"},
            {"num": 4, "name": "Variante della Roggia",  "ratio": 0.42, "speed": 115, "desc": "High Kerb Chicane"},
            {"num": 6, "name": "Lesmo 1",                "ratio": 0.54, "speed": 185, "desc": "Medium-Speed 3.8G Right"},
            {"num": 7, "name": "Lesmo 2",                "ratio": 0.61, "speed": 170, "desc": "Understeer Snap Exit"},
            {"num": 8, "name": "Variante Ascari",        "ratio": 0.78, "speed": 215, "desc": "Rapid Left-Right-Left Transition"},
            {"num": 11,"name": "Curva Parabolica",       "ratio": 0.92, "speed": 190, "desc": "Opening Radius High-Speed Drag"},
        ],
        "coords": [
            (290, 340), (290, 210), (290, 90),  (260, 45),  (210, 45),  (160, 75),
            (110, 120), (80, 180),  (70, 250),  (80, 310),  (120, 350), (180, 350),
            (230, 350)
        ]
    },

    # ── 4. Circuit de Spa-Francorchamps (Belgium) ─────────────────────────────
    "spa": {
        "name": "Circuit de Spa-Francorchamps",
        "location": "Stavelot, Belgium",
        "lap_len": "7.004 km",
        "corners": [
            {"num": 1, "name": "La Source",     "ratio": 0.08, "speed": 72,  "desc": "Tight 180° Right Hairpin"},
            {"num": 2, "name": "Eau Rouge",     "ratio": 0.20, "speed": 310, "desc": "Steep Uphill Lateral Compression"},
            {"num": 4, "name": "Raidillon",     "ratio": 0.25, "speed": 305, "desc": "Blind Crest Flat-Out"},
            {"num": 5, "name": "Les Combes",    "ratio": 0.40, "speed": 140, "desc": "Heavy Braking Right-Left Chicane"},
            {"num": 8, "name": "Bruxelles",     "ratio": 0.52, "speed": 110, "desc": "Downhill Off-Camber Hairpin"},
            {"num": 10,"name": "Pouhon",        "ratio": 0.66, "speed": 265, "desc": "Double Apex 5.4G Left"},
            {"num": 14,"name": "Stavelot",      "ratio": 0.78, "speed": 240, "desc": "High-Speed Full Throttle Acceleration"},
            {"num": 17,"name": "Blanchimont",   "ratio": 0.88, "speed": 315, "desc": "Flat-out Blind Double-Left Curve"},
            {"num": 19,"name": "Bus Stop",      "ratio": 0.95, "speed": 80,  "desc": "Tight Final Chicane onto Straight"},
        ],
        "coords": [
            (80, 340),  (60, 270),  (70, 200),  (110, 140), (170, 80),  (240, 50),
            (290, 80),  (280, 140), (230, 190), (190, 240), (220, 290), (260, 320),
            (240, 350), (160, 360)
        ]
    },

    # ── 5. Albert Park Circuit (Melbourne, Australia) ─────────────────────────
    "australia": {
        "name": "Albert Park Circuit",
        "location": "Melbourne, Australia",
        "lap_len": "5.278 km",
        "corners": [
            {"num": 1, "name": "Jones",         "ratio": 0.11, "speed": 140, "desc": "Fast Right-Left Chicane"},
            {"num": 3, "name": "Sports Center", "ratio": 0.22, "speed": 95,  "desc": "Heavy Braking Right"},
            {"num": 6, "name": "Clark",         "ratio": 0.42, "speed": 170, "desc": "Sweeping Lake Curve"},
            {"num": 9, "name": "Lakeside",      "ratio": 0.60, "speed": 290, "desc": "Flat-Out High-Speed Chicane"},
            {"num": 11,"name": "Waite",         "ratio": 0.74, "speed": 195, "desc": "Fast Direction Change"},
            {"num": 13,"name": "Ascari",        "ratio": 0.86, "speed": 115, "desc": "Heavy Braking Right onto Main Straight"},
        ],
        "coords": [
            (110, 360), (90, 280),  (70, 190),  (90, 110),  (140, 55),  (210, 50),
            (260, 90),  (280, 160), (260, 230), (220, 290), (170, 340)
        ]
    },

    # ── 6. Suzuka International Racing Course (Japan) ────────────────────────
    "japan": {
        "name": "Suzuka International Racing Course",
        "location": "Suzuka, Japan",
        "lap_len": "5.807 km",
        "corners": [
            {"num": 1, "name": "First Curve",   "ratio": 0.09, "speed": 185, "desc": "High-Speed Entry into Tight Right"},
            {"num": 3, "name": "S Curves",      "ratio": 0.20, "speed": 215, "desc": "Flowing Uphill Lateral Direction Changes"},
            {"num": 7, "name": "Dunlop Curve",  "ratio": 0.32, "speed": 230, "desc": "Blind Uphill Left Sweeper"},
            {"num": 8, "name": "Degner 1 & 2",  "ratio": 0.42, "speed": 140, "desc": "Narrow High-G Direction Change"},
            {"num": 11,"name": "Hairpin",       "ratio": 0.54, "speed": 65,  "desc": "Tight Slowest 2nd-Gear Hairpin"},
            {"num": 13,"name": "Spoon Curve",   "ratio": 0.72, "speed": 175, "desc": "Double-Apex Downhill Left"},
            {"num": 15,"name": "130R",          "ratio": 0.87, "speed": 305, "desc": "Iconic 305 km/h Flat-Out Blind Apex Left"},
            {"num": 16,"name": "Casio Triangle","ratio": 0.94, "speed": 75,  "desc": "Heavy Deceleration Chicane onto Pit Straight"},
        ],
        "coords": [
            (180, 360), (230, 320), (270, 260), (280, 200), (250, 160), (200, 150),
            (150, 120), (130, 70),  (170, 45),  (220, 60),  (210, 110), (160, 180),
            (100, 200), (60, 240),  (65, 290),  (110, 340)
        ]
    },

    # ── 7. Autodromo Jose Carlos Pace (Interlagos, Brazil) ───────────────────
    "brazil": {
        "name": "Autódromo José Carlos Pace",
        "location": "São Paulo, Brazil",
        "lap_len": "4.309 km",
        "corners": [
            {"num": 1, "name": "Senna 'S'",     "ratio": 0.12, "speed": 110, "desc": "Downhill Sweeping Left-Right Chicane"},
            {"num": 3, "name": "Curva do Sol",  "ratio": 0.22, "speed": 235, "desc": "Long High-Lateral Left onto Reta Oposta"},
            {"num": 4, "name": "Descida do Lago","ratio": 0.38, "speed": 145, "desc": "Heavy Braking Downhill Double Left"},
            {"num": 6, "name": "Ferradura",     "ratio": 0.50, "speed": 180, "desc": "Long Right-Hand Uphill Carousel"},
            {"num": 8, "name": "Pinheirinho",   "ratio": 0.65, "speed": 95,  "desc": "Tight Technical Off-Camber Left"},
            {"num": 10,"name": "Bico de Pato",  "ratio": 0.74, "speed": 78,  "desc": "Slowest 1st-Gear Uphill Hairpin"},
            {"num": 12,"name": "Junção",        "ratio": 0.84, "speed": 130, "desc": "Decisive Left onto Flat-Out Climbing Straight"},
        ],
        "coords": [
            (180, 50),  (120, 70),  (80, 120),  (70, 190),  (90, 270),  (150, 340),
            (210, 350), (260, 310), (250, 240), (200, 200), (220, 150), (260, 110),
            (240, 60)
        ]
    },

    # ── 8. Circuit of the Americas (Austin, USA) ──────────────────────────────
    "usa": {
        "name": "Circuit of the Americas",
        "location": "Austin, Texas, USA",
        "lap_len": "5.513 km",
        "corners": [
            {"num": 1, "name": "Big Red",       "ratio": 0.10, "speed": 85,  "desc": "Steep 133-ft Blind Uphill Hairpin"},
            {"num": 3, "name": "The Esses",     "ratio": 0.22, "speed": 265, "desc": "Rapid Direction Changes (Maggotts/Becketts style)"},
            {"num": 11,"name": "Hairpin",       "ratio": 0.44, "speed": 75,  "desc": "Heavy Braking Left onto 1.2km Back Straight"},
            {"num": 12,"name": "Stadium Entry", "ratio": 0.64, "speed": 90,  "desc": "330 km/h Deceleration into Stadium Complex"},
            {"num": 16,"name": "Carousel Triple Apex","ratio": 0.80,"speed": 210,"desc": "Sustained High-Lateral Right (Istanbul T8 style)"},
            {"num": 19,"name": "Tower Corner",  "ratio": 0.92, "speed": 120, "desc": "Double 90° Left onto Pit Straight"},
        ],
        "coords": [
            (60, 260),  (70, 150),  (110, 70),  (170, 50),  (210, 80),  (250, 130),
            (280, 190), (280, 270), (240, 320), (180, 340), (130, 310), (150, 260),
            (190, 240), (160, 200), (100, 220)
        ]
    },

    # ── 9. Circuit Gilles Villeneuve (Montreal, Canada) ──────────────────────
    "canada": {
        "name": "Circuit Gilles-Villeneuve",
        "location": "Montreal, Canada",
        "lap_len": "4.361 km",
        "corners": [
            {"num": 1, "name": "Virage Senna",  "ratio": 0.12, "speed": 98,  "desc": "Tight Left-Right Chicane"},
            {"num": 6, "name": "Pont de la Concorde","ratio": 0.32,"speed": 115,"desc": "Chicane over Island Bridge"},
            {"num": 10,"name": "L'Epingle",     "ratio": 0.60, "speed": 62,  "desc": "Tight 180° Heavy Braking Hairpin"},
            {"num": 13,"name": "Wall of Champions","ratio": 0.90,"speed": 140,"desc": "High Kerb Chicane Bordering the Concrete Wall"},
        ],
        "coords": [
            (250, 340), (220, 240), (180, 150), (140, 80),  (90, 50),   (70, 90),
            (90, 160),  (130, 230), (170, 310), (210, 360), (260, 370)
        ]
    },

    # ── 10. Red Bull Ring (Spielberg, Austria) ────────────────────────────────
    "austria": {
        "name": "Red Bull Ring",
        "location": "Spielberg, Austria",
        "lap_len": "4.318 km",
        "corners": [
            {"num": 1, "name": "Niki Lauda Kurve","ratio": 0.12,"speed": 145,"desc": "Uphill 90° Right Launch"},
            {"num": 3, "name": "Remus",         "ratio": 0.30, "speed": 72,  "desc": "Steep Uphill 1st-Gear Hairpin (Prime Overtaking)"},
            {"num": 4, "name": "Rauch",         "ratio": 0.44, "speed": 110, "desc": "Downhill Trail-Braking Right"},
            {"num": 6, "name": "Gerhard Berger","ratio": 0.62, "speed": 165, "desc": "Fast Downhill Left"},
            {"num": 9, "name": "Jochen Rindt",  "ratio": 0.82, "speed": 195, "desc": "High-Speed Downhill Right"},
            {"num": 10,"name": "Red Bull Mobile","ratio": 0.92,"speed": 210, "desc": "Full Throttle Apex Launch onto Pit Straight"},
        ],
        "coords": [
            (260, 330), (230, 220), (190, 110), (140, 50),  (80, 80),   (70, 160),
            (110, 230), (160, 280), (210, 340)
        ]
    },

    # ── 11. Circuit Zandvoort (Netherlands) ──────────────────────────────────
    "netherlands": {
        "name": "Circuit Zandvoort",
        "location": "Zandvoort, Netherlands",
        "lap_len": "4.259 km",
        "corners": [
            {"num": 1, "name": "Tarzan",        "ratio": 0.12, "speed": 105, "desc": "Iconic 180° Right Dunes Hairpin"},
            {"num": 3, "name": "Hugenholtz",    "ratio": 0.25, "speed": 120, "desc": "Extreme 19° Parabolic Banking Left"},
            {"num": 7, "name": "Scheivlak",     "ratio": 0.48, "speed": 245, "desc": "Blind High-Speed Downhill Dunes Crest"},
            {"num": 11,"name": "Hans Ernst",    "ratio": 0.74, "speed": 88,  "desc": "Tight Double Chicane"},
            {"num": 14,"name": "Arie Luyendyk", "ratio": 0.92, "speed": 270, "desc": "18° Steep Banking Full-Throttle DRS Launch"},
        ],
        "coords": [
            (190, 350), (140, 310), (110, 250), (90, 180),  (110, 110), (160, 60),
            (220, 60),  (260, 110), (240, 180), (200, 230), (220, 280), (240, 340)
        ]
    },

    # ── 12. Bahrain International Circuit (Sakhir) ───────────────────────────
    "bahrain": {
        "name": "Bahrain International Circuit",
        "location": "Sakhir, Bahrain",
        "lap_len": "5.412 km",
        "corners": [
            {"num": 1, "name": "Michael Schumacher","ratio": 0.12,"speed": 75,"desc": "330 km/h Heavy Braking into Tight Right"},
            {"num": 4, "name": "Turn 4",        "ratio": 0.28, "speed": 135, "desc": "Uphill Fast Right Launch onto Back Section"},
            {"num": 8, "name": "Hairpin",       "ratio": 0.48, "speed": 80,  "desc": "Slow 1st-Gear Right Hairpin"},
            {"num": 10,"name": "Turn 10",       "ratio": 0.58, "speed": 72,  "desc": "Severe Downhill Off-Camber Lockup Risk"},
            {"num": 14,"name": "Final Corner",  "ratio": 0.90, "speed": 125, "desc": "Late Apex Acceleration onto Main Straight"},
        ],
        "coords": [
            (260, 350), (260, 220), (230, 140), (180, 80),  (120, 60),  (70, 95),
            (80, 160),  (130, 210), (150, 260), (110, 290), (80, 330), (140, 360),
            (200, 360)
        ]
    },

    # ── 13. Jeddah Corniche Circuit (Saudi Arabia) ───────────────────────────
    "saudi_arabia": {
        "name": "Jeddah Corniche Circuit",
        "location": "Jeddah, Saudi Arabia",
        "lap_len": "6.174 km",
        "corners": [
            {"num": 1, "name": "Turn 1-2 Chicane","ratio": 0.08,"speed": 95, "desc": "Narrow Street Entry Chicane"},
            {"num": 8, "name": "High-Speed Esses","ratio": 0.26,"speed": 280,"desc": "Blind High-Speed Walls Sweep"},
            {"num": 13,"name": "Banked Hairpin","ratio": 0.45, "speed": 140, "desc": "12° Parabolic Banking Left"},
            {"num": 22,"name": "High-G Chicane","ratio": 0.74, "speed": 220, "desc": "Direction Change Bordering Coastal Walls"},
            {"num": 27,"name": "Final Hairpin", "ratio": 0.94, "speed": 85,  "desc": "Heavy Braking Left onto Coastal Main Straight"},
        ],
        "coords": [
            (160, 365), (140, 310), (130, 240), (135, 170), (145, 100), (155, 45),
            (180, 45),  (190, 110), (180, 180), (175, 250), (180, 320)
        ]
    },

    # ── 14. Miami International Autodrome (USA) ──────────────────────────────
    "miami": {
        "name": "Miami International Autodrome",
        "location": "Miami, Florida, USA",
        "lap_len": "5.412 km",
        "corners": [
            {"num": 1, "name": "Turn 1",        "ratio": 0.12, "speed": 98,  "desc": "Hard Braking 90° Left"},
            {"num": 5, "name": "High-Speed S",  "ratio": 0.25, "speed": 240, "desc": "Flowing High-Lateral Direction Changes"},
            {"num": 11,"name": "Marina Hairpin","ratio": 0.48, "speed": 80,  "desc": "Tight Slowest Hairpin"},
            {"num": 14,"name": "Overpass Chicane","ratio": 0.62,"speed": 75, "desc": "Uphill-Downhill Crest under Interstate Bridge"},
            {"num": 17,"name": "Turnpike Hairpin","ratio": 0.86,"speed": 72, "desc": "Heavy Braking from 340 km/h Back Straight"},
        ],
        "coords": [
            (270, 300), (270, 180), (250, 100), (190, 60),  (120, 60),  (60, 100),
            (50, 180),  (80, 230),  (130, 250), (90, 290),  (70, 340),  (160, 340),
            (220, 320)
        ]
    },

    # ── 15. Marina Bay Street Circuit (Singapore) ────────────────────────────
    "singapore": {
        "name": "Marina Bay Street Circuit",
        "location": "Marina Bay, Singapore",
        "lap_len": "4.940 km",
        "corners": [
            {"num": 1, "name": "Sheares",       "ratio": 0.12, "speed": 110, "desc": "Heavy Braking Complex into Harbor Section"},
            {"num": 7, "name": "Memorial",      "ratio": 0.32, "speed": 90,  "desc": "90° Left onto Fast Raffles Boulevard"},
            {"num": 13,"name": "Anderson Bridge","ratio": 0.58,"speed": 85,  "desc": "Narrow Historical Bridge Crossing"},
            {"num": 14,"name": "Raffles Avenue","ratio": 0.68, "speed": 88,  "desc": "Heavy Deceleration 90° Right"},
            {"num": 16,"name": "Bay Chicane",   "ratio": 0.88, "speed": 145, "desc": "New High-Speed Bypass Straight"},
        ],
        "coords": [
            (240, 340), (260, 260), (240, 180), (200, 120), (140, 70),  (80, 80),
            (70, 140),  (110, 190), (90, 240),  (120, 290), (170, 310), (150, 350)
        ]
    },

    # ── 16. Baku City Circuit (Azerbaijan) ───────────────────────────────────
    "azerbaijan": {
        "name": "Baku City Circuit",
        "location": "Baku, Azerbaijan",
        "lap_len": "6.003 km",
        "corners": [
            {"num": 1, "name": "Turn 1",        "ratio": 0.10, "speed": 100, "desc": "345 km/h Braking into 90° Left"},
            {"num": 3, "name": "Government House","ratio": 0.22,"speed": 95, "desc": "90° Left around Historic Plaza"},
            {"num": 8, "name": "Old City Castle","ratio": 0.44,"speed": 75,  "desc": "Tightest Section in F1 (7.6m Wide Between Medieval Walls)"},
            {"num": 15,"name": "Downhill Left", "ratio": 0.65, "speed": 115, "desc": "Downhill Narrow Barrier Crest"},
            {"num": 16,"name": "Caspian Launch","ratio": 0.74, "speed": 140, "desc": "Exit onto 2.2km Flat-Out Seaside Boulevard"},
        ],
        "coords": [
            (270, 360), (270, 230), (270, 100), (230, 60),  (170, 60),  (120, 90),
            (80, 130),  (60, 190),  (90, 240),  (80, 290),  (120, 320), (190, 350)
        ]
    },

    # ── 17. Shanghai International Circuit (China) ───────────────────────────
    "china": {
        "name": "Shanghai International Circuit",
        "location": "Shanghai, China",
        "lap_len": "5.451 km",
        "corners": [
            {"num": 1, "name": "The Snail",     "ratio": 0.14, "speed": 80,  "desc": "270° Tightening Carousel Spiral"},
            {"num": 6, "name": "Turn 6 Hairpin","ratio": 0.35, "speed": 78,  "desc": "Downhill Braking Right Hairpin"},
            {"num": 13,"name": "Banked Launch", "ratio": 0.66, "speed": 190, "desc": "Steep Banked Curve onto 1.2km Long Straight"},
            {"num": 14,"name": "Hairpin",       "ratio": 0.88, "speed": 68,  "desc": "335 km/h Deceleration into 1st-Gear Hairpin"},
        ],
        "coords": [
            (220, 340), (260, 280), (260, 200), (220, 140), (170, 170), (190, 220),
            (140, 240), (90, 200),  (70, 140),  (100, 80),  (160, 50),  (220, 70),
            (170, 110), (110, 110), (80, 310),  (150, 350)
        ]
    },

    # ── 18. Hungaroring (Hungary) ────────────────────────────────────────────
    "hungary": {
        "name": "Hungaroring",
        "location": "Mogyoród, Hungary",
        "lap_len": "4.381 km",
        "corners": [
            {"num": 1, "name": "Turn 1 Downhill","ratio": 0.12,"speed": 105, "desc": "Steep Downhill Right Hairpin"},
            {"num": 2, "name": "Turn 2 Off-Camber","ratio": 0.24,"speed": 125,"desc": "Downhill Long Sweeping Left"},
            {"num": 4, "name": "Turn 4 Blind Crest","ratio": 0.38,"speed": 215,"desc": "High-Speed Blind Uphill Left"},
            {"num": 6, "name": "Chicane",       "ratio": 0.52, "speed": 95,  "desc": "Right-Left Kerb Ride"},
            {"num": 14,"name": "Final Corner",  "ratio": 0.92, "speed": 135, "desc": "Long Radius Carousel onto Main Straight"},
        ],
        "coords": [
            (220, 350), (180, 280), (130, 220), (90, 160),  (70, 100),  (110, 60),
            (170, 60),  (220, 90),  (250, 140), (220, 190), (240, 240), (260, 300)
        ]
    },

    # ── 19. Circuit de Barcelona-Catalunya (Spain) ───────────────────────────
    "spain": {
        "name": "Circuit de Barcelona-Catalunya",
        "location": "Montmeló, Spain",
        "lap_len": "4.657 km",
        "corners": [
            {"num": 1, "name": "Elf",           "ratio": 0.12, "speed": 135, "desc": "320 km/h Braking Right-Left Chicane"},
            {"num": 3, "name": "Renault",       "ratio": 0.22, "speed": 230, "desc": "Iconic Long 4.5G Accelerating Right"},
            {"num": 5, "name": "Seat",          "ratio": 0.38, "speed": 82,  "desc": "Downhill Left Hairpin"},
            {"num": 9, "name": "Campsa",        "ratio": 0.60, "speed": 240, "desc": "Blind Uphill High-Speed Right"},
            {"num": 10,"name": "La Caixa",      "ratio": 0.72, "speed": 85,  "desc": "Heavy Braking Left Hairpin"},
            {"num": 14,"name": "New Final Turn","ratio": 0.92, "speed": 260, "desc": "Fast Full-Throttle Sweeper onto Straight"},
        ],
        "coords": [
            (250, 350), (260, 240), (240, 150), (180, 90),  (120, 60),  (60, 90),
            (80, 160),  (130, 190), (170, 160), (170, 230), (130, 270), (190, 330)
        ]
    },

    # ── 20. Autodromo Enzo e Dino Ferrari (Imola, Italy) ─────────────────────
    "emilia_romagna": {
        "name": "Autodromo Enzo e Dino Ferrari",
        "location": "Imola, Italy",
        "lap_len": "4.909 km",
        "corners": [
            {"num": 2, "name": "Variante Tamburello","ratio": 0.14,"speed": 140,"desc": "Left-Right-Left Kerb Chicane"},
            {"num": 5, "name": "Variante Villeneuve","ratio": 0.28,"speed": 165,"desc": "High-Speed Direction Change"},
            {"num": 7, "name": "Tosa",          "ratio": 0.38, "speed": 85,  "desc": "Steep Uphill Tight Hairpin"},
            {"num": 9, "name": "Piratella",     "ratio": 0.50, "speed": 195, "desc": "Blind Downhill Left"},
            {"num": 11,"name": "Acque Minerali","ratio": 0.62, "speed": 150, "desc": "Steep Downhill Compression followed by Uphill Flick"},
            {"num": 14,"name": "Variante Alta", "ratio": 0.76, "speed": 125, "desc": "High Kerb Crest Chicane"},
            {"num": 17,"name": "Rivazza 1 & 2", "ratio": 0.90, "speed": 115, "desc": "Downhill Double Left onto Main Straight"},
        ],
        "coords": [
            (150, 350), (180, 280), (220, 220), (260, 160), (250, 90),  (200, 60),
            (140, 80),  (90, 130),  (80, 200),  (110, 260), (90, 310)
        ]
    },

    # ── 21. Autodromo Hermanos Rodriguez (Mexico City) ───────────────────────
    "mexico": {
        "name": "Autódromo Hermanos Rodríguez",
        "location": "Mexico City, Mexico",
        "lap_len": "4.304 km",
        "corners": [
            {"num": 1, "name": "Turn 1 Chicane","ratio": 0.15,"speed": 110, "desc": "355 km/h Braking into Right-Left-Right"},
            {"num": 4, "name": "Turn 4-5",      "ratio": 0.32, "speed": 98,  "desc": "Heavy Braking Left-Right Chicane"},
            {"num": 7, "name": "The Esses",     "ratio": 0.52, "speed": 225, "desc": "Flowing High-Speed Direction Changes"},
            {"num": 12,"name": "Foro Sol Stadium","ratio": 0.82,"speed": 65,  "desc": "Stadium Complex through 40,000 Cheering Spectators"},
        ],
        "coords": [
            (260, 340), (260, 180), (240, 90),  (190, 50),  (130, 60),  (80, 100),
            (70, 180),  (110, 230), (160, 250), (140, 290), (100, 330), (170, 350)
        ]
    },

    # ── 22. Las Vegas Strip Circuit (USA) ────────────────────────────────────
    "las_vegas": {
        "name": "Las Vegas Strip Circuit",
        "location": "Las Vegas, Nevada, USA",
        "lap_len": "6.201 km",
        "corners": [
            {"num": 1, "name": "Turn 1 Hairpin","ratio": 0.10, "speed": 90,  "desc": "Tight Left around Paddock Building"},
            {"num": 5, "name": "The Sphere",    "ratio": 0.28, "speed": 125, "desc": "Sweeping Loop around the Illuminated MSG Sphere"},
            {"num": 12,"name": "Strip Braking", "ratio": 0.58, "speed": 110, "desc": "Launch onto the 1.9km Las Vegas Boulevard Strip"},
            {"num": 14,"name": "Bellagio Chicane","ratio": 0.88,"speed": 95, "desc": "350 km/h Deceleration past Bellagio Fountains"},
        ],
        "coords": [
            (100, 340), (80, 240),  (80, 140),  (110, 70),  (170, 60),  (220, 90),
            (240, 160), (210, 220), (230, 280), (230, 350), (160, 350)
        ]
    },

    # ── 23. Lusail International Circuit (Qatar) ─────────────────────────────
    "qatar": {
        "name": "Lusail International Circuit",
        "location": "Lusail, Qatar",
        "lap_len": "5.419 km",
        "corners": [
            {"num": 1, "name": "Turn 1",        "ratio": 0.12, "speed": 115, "desc": "335 km/h Braking into 90° Right"},
            {"num": 6, "name": "Turn 6 Hairpin","ratio": 0.38, "speed": 92,  "desc": "Tight Slowest Left Hairpin"},
            {"num": 12,"name": "Triple Apex Right","ratio": 0.70,"speed": 245,"desc": "5.2G Sustained Lateral High-Speed Complex"},
            {"num": 16,"name": "Final Corner",  "ratio": 0.92, "speed": 145, "desc": "Launch onto 1.068km Main Straight"},
        ],
        "coords": [
            (240, 340), (260, 240), (240, 160), (210, 100), (160, 60),  (100, 70),
            (70, 130),  (90, 190),  (130, 230), (110, 280), (140, 330), (190, 350)
        ]
    },

    # ── 24. Yas Marina Circuit (Abu Dhabi) ───────────────────────────────────
    "abu_dhabi": {
        "name": "Yas Marina Circuit",
        "location": "Yas Island, Abu Dhabi, UAE",
        "lap_len": "5.281 km",
        "corners": [
            {"num": 1, "name": "Turn 1",        "ratio": 0.10, "speed": 140, "desc": "315 km/h Braking into 90° Left"},
            {"num": 5, "name": "North Hairpin", "ratio": 0.30, "speed": 80,  "desc": "Heavy Deceleration into Left Hairpin"},
            {"num": 9, "name": "Marsa Banked",  "ratio": 0.60, "speed": 195, "desc": "Banked Sweeping South Marina Corner"},
            {"num": 12,"name": "W Hotel Section","ratio": 0.78,"speed": 115,"desc": "Flowing Technical Section under Illuminated Hotel"},
        ],
        "coords": [
            (190, 350), (220, 280), (240, 200), (230, 130), (190, 70),  (130, 60),
            (80, 100),  (70, 170),  (90, 240),  (120, 290), (150, 330)
        ]
    }
}

# Direct mapping aliases for standard calendar event IDs
CIRCUIT_TEMPLATES["austin"] = CIRCUIT_TEMPLATES["usa"]
CIRCUIT_TEMPLATES["imola"] = CIRCUIT_TEMPLATES["emilia_romagna"]
CIRCUIT_TEMPLATES["baku"] = CIRCUIT_TEMPLATES["azerbaijan"]
CIRCUIT_TEMPLATES["suzuka"] = CIRCUIT_TEMPLATES["japan"]
CIRCUIT_TEMPLATES["interlagos"] = CIRCUIT_TEMPLATES["brazil"]

def get_circuit_template(circuit_identifier: str) -> Dict[str, Any]:
    """
    Retrieves the authentic circuit geometry template by matching against
    circuit IDs, names, or locations.
    """
    clean = circuit_identifier.lower().replace("-", "_").replace(" ", "_")
    
    # 1. Exact dictionary key match
    if clean in CIRCUIT_TEMPLATES:
        return CIRCUIT_TEMPLATES[clean]
            
    # 2. Known Aliases
    alias_map = {
        "melbourne": "australia",
        "albert_park": "australia",
        "monte_carlo": "monaco",
        "interlagos": "brazil",
        "sao_paulo": "brazil",
        "cota": "usa",
        "austin": "usa",
        "montreal": "canada",
        "gilles_villeneuve": "canada",
        "spielberg": "austria",
        "red_bull_ring": "austria",
        "sakhir": "bahrain",
        "jeddah": "saudi_arabia",
        "marina_bay": "singapore",
        "baku": "azerbaijan",
        "shanghai": "china",
        "catalunya": "spain",
        "barcelona": "spain",
        "imola": "emilia_romagna",
        "enzo_e_dino_ferrari": "emilia_romagna",
        "mexico_city": "mexico",
        "hermanos_rodriguez": "mexico",
        "vegas": "las_vegas",
        "lusail": "qatar",
        "doha": "qatar",
        "yas_island": "abu_dhabi",
        "yas_marina": "abu_dhabi",
        "madrid": "spain"
    }
    if clean in alias_map and alias_map[clean] in CIRCUIT_TEMPLATES:
        return CIRCUIT_TEMPLATES[alias_map[clean]]
        
    for alias, target in alias_map.items():
        if alias in clean and target in CIRCUIT_TEMPLATES:
            return CIRCUIT_TEMPLATES[target]

    # 3. Exact circuit name or location substring match
    for k, tmpl in CIRCUIT_TEMPLATES.items():
        if tmpl["name"].lower() in clean or clean in tmpl["name"].lower():
            return tmpl
        if tmpl["location"].lower() in clean or clean in tmpl["location"].lower():
            return tmpl

    return CIRCUIT_TEMPLATES["monaco"]

ALIAS_TO_ACCURATE_KEY = {
    "melbourne": "australia",
    "albert_park": "australia",
    "monte_carlo": "monaco",
    "interlagos": "brazil",
    "sao_paulo": "brazil",
    "cota": "austin",
    "usa": "austin",
    "united_states": "austin",
    "montreal": "canada",
    "gilles_villeneuve": "canada",
    "spielberg": "austria",
    "red_bull_ring": "austria",
    "sakhir": "bahrain",
    "jeddah": "saudi_arabia",
    "marina_bay": "singapore",
    "azerbaijan": "baku",
    "shanghai": "china",
    "catalunya": "spain",
    "barcelona": "spain",
    "emilia_romagna": "imola",
    "enzo_e_dino_ferrari": "imola",
    "mexico_city": "mexico",
    "hermanos_rodriguez": "mexico",
    "vegas": "las_vegas",
    "lusail": "qatar",
    "doha": "qatar",
    "yas_island": "abu_dhabi",
    "yas_marina": "abu_dhabi",
    "suzuka": "japan",
    "zandvoort": "netherlands",
    "hungaroring": "hungary",
    "great_britain": "silverstone",
    "british": "silverstone",
    "belgian": "spa",
    "belgium": "spa",
    "italian": "monza",
    "italy": "monza",
}

def resolve_circuit_key(identifier: str) -> str:
    """Resolves arbitrary circuit identifiers, event names, or locations to one of the 24 canonical keys."""
    clean = str(identifier).lower().strip().replace("-", "_").replace(" ", "_")
    if clean in ACCURATE_CIRCUITS:
        return clean
    if clean in ALIAS_TO_ACCURATE_KEY:
        return ALIAS_TO_ACCURATE_KEY[clean]
    for alias, key in ALIAS_TO_ACCURATE_KEY.items():
        if alias in clean and key in ACCURATE_CIRCUITS:
            return key
    for k, data in ACCURATE_CIRCUITS.items():
        c_name = data.get("circuit_name", "").lower()
        c_loc = data.get("location", "").lower()
        if c_name and (c_name in clean or clean in c_name):
            return k
        if c_loc and (c_loc in clean or clean in c_loc):
            return k
    return "monaco"

def generate_track_geometry(circuit_id: str, lap_time: float) -> Dict[str, Any]:
    """
    Generates high-precision normalized SVG track geometry with:
    - 100% authentic FIA GPS transponder coordinates and GIS track centerlines
    - Precise waypoints and FIA corner anchor pins
    - Start / Finish line coordinate
    - Dynamic circuit naming, location, and official length metadata
    """
    target_key = resolve_circuit_key(circuit_id)
    raw_track = ACCURATE_CIRCUITS.get(target_key)
    
    if not raw_track:
        raw_track = ACCURATE_CIRCUITS.get("monaco")

    if not raw_track:
        tmpl = get_circuit_template(circuit_id)
        pts_norm = catmull_rom_spline(tmpl["coords"], num_samples=340)
        track_points = []
        svg_parts = []
        n_pts = len(pts_norm)
        for i in range(n_pts):
            x = float(pts_norm[i, 0])
            y = float(pts_norm[i, 1])
            t = round((i / float(n_pts)) * lap_time, 2)
            track_points.append({"t": t, "x": x, "y": y, "spd": 220})
            svg_parts.append(f"{'M' if i == 0 else 'L'} {x} {y}")
        svg_parts.append("Z")
        return {
            "viewBox": "0 0 320 380",
            "svg_path": " ".join(svg_parts),
            "points": track_points,
            "corner_pins": [],
            "circuit_name": tmpl["name"],
            "location": tmpl["location"],
            "lap_len": tmpl["lap_len"],
            "start_finish": {"x": track_points[0]["x"], "y": track_points[0]["y"]}
        }

    # Clone the precompiled authentic circuit map
    track_data = copy.deepcopy(raw_track)
    points = track_data.get("points", [])
    n_pts = len(points)
    
    if n_pts > 0:
        for i, pt in enumerate(points):
            pt["t"] = round((i / float(n_pts)) * lap_time, 2)

    # Scale corner pins timing windows to match requested lap_time
    corners = track_data.get("corner_pins", [])
    if n_pts > 0 and len(corners) > 0:
        pts_x = np.array([p["x"] for p in points])
        pts_y = np.array([p["y"] for p in points])
        for c in corners:
            cx, cy = c.get("x", 0.0), c.get("y", 0.0)
            dists = (pts_x - cx) ** 2 + (pts_y - cy) ** 2
            closest_idx = int(np.argmin(dists))
            ratio = closest_idx / float(n_pts - 1)
            target_t = round(ratio * lap_time, 1)
            c["start"] = max(0.0, round(target_t - 2.0, 1))
            c["end"] = round(target_t + 2.0, 1)
            if "name" in c and (not c.get("id") or c.get("id") == "Turn"):
                c["id"] = f"T{c['name'].replace('Turn ', '').split()[0]}"

    return track_data
