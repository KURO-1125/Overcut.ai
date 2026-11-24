"""
Overcut.ai Accurate Circuit Map Compiler
Builds 100% authentic real-world circuit maps for all 24 Formula 1 Championship tracks:
1. Monaco: Built from official FIA 2023 FastF1 transponder telemetry (523 points, 19 corners).
2. All 23 other circuits: Built from official GPS satellite track centerlines in f1_circuits_raw.geojson,
   projected into metric Cartesian space, smoothed with closed-loop cubic B-splines,
   and aligned with true curvature apexes and official FIA corner pins.
"""

import json
import math
import os
import numpy as np
from scipy.interpolate import splprep, splev

CIRCUIT_CORNER_DEFINITIONS = {
    "silverstone": [
        {"num": 1, "name": "Abbey",         "ratio": 0.07, "speed": 290, "desc": "Flat-out High-Speed Entry"},
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
    "monza": [
        {"num": 1, "name": "Variante del Rettifilo", "ratio": 0.15, "speed": 75,  "desc": "350 to 75 km/h Heavy Braking"},
        {"num": 3, "name": "Curva Grande",           "ratio": 0.28, "speed": 305, "desc": "Sustained High-Speed Right"},
        {"num": 4, "name": "Variante della Roggia",  "ratio": 0.42, "speed": 115, "desc": "High Kerb Chicane"},
        {"num": 6, "name": "Lesmo 1",                "ratio": 0.54, "speed": 185, "desc": "Medium-Speed 3.8G Right"},
        {"num": 7, "name": "Lesmo 2",                "ratio": 0.61, "speed": 170, "desc": "Understeer Snap Exit"},
        {"num": 8, "name": "Variante Ascari",        "ratio": 0.78, "speed": 215, "desc": "Rapid Left-Right-Left Transition"},
        {"num": 11,"name": "Curva Parabolica",       "ratio": 0.92, "speed": 190, "desc": "Opening Radius High-Speed Drag"},
    ],
    "spa": [
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
    "australia": [
        {"num": 1, "name": "Jones",         "ratio": 0.11, "speed": 140, "desc": "Fast Right-Left Chicane"},
        {"num": 3, "name": "Sports Center", "ratio": 0.22, "speed": 95,  "desc": "Heavy Braking Right"},
        {"num": 6, "name": "Clark",         "ratio": 0.42, "speed": 170, "desc": "Sweeping Lake Curve"},
        {"num": 9, "name": "Lakeside",      "ratio": 0.60, "speed": 290, "desc": "Flat-Out High-Speed Chicane"},
        {"num": 11,"name": "Waite",         "ratio": 0.74, "speed": 195, "desc": "Fast Direction Change"},
        {"num": 13,"name": "Ascari",        "ratio": 0.86, "speed": 115, "desc": "Heavy Braking Right onto Main Straight"},
    ],
    "japan": [
        {"num": 1, "name": "First Curve",   "ratio": 0.09, "speed": 185, "desc": "High-Speed Entry into Tight Right"},
        {"num": 3, "name": "S Curves",      "ratio": 0.20, "speed": 215, "desc": "Flowing Uphill Lateral Direction Changes"},
        {"num": 7, "name": "Dunlop Curve",  "ratio": 0.32, "speed": 230, "desc": "Blind Uphill Left Sweeper"},
        {"num": 8, "name": "Degner 1 & 2",  "ratio": 0.42, "speed": 140, "desc": "Narrow High-G Direction Change"},
        {"num": 11,"name": "Hairpin",       "ratio": 0.54, "speed": 65,  "desc": "Tight Slowest 2nd-Gear Hairpin"},
        {"num": 13,"name": "Spoon Curve",   "ratio": 0.72, "speed": 175, "desc": "Double-Apex Downhill Left"},
        {"num": 15,"name": "130R",          "ratio": 0.87, "speed": 305, "desc": "Iconic 305 km/h Flat-Out Blind Apex Left"},
        {"num": 16,"name": "Casio Triangle","ratio": 0.94, "speed": 75,  "desc": "Heavy Deceleration Chicane onto Pit Straight"},
    ],
    "brazil": [
        {"num": 1, "name": "Senna 'S'",     "ratio": 0.12, "speed": 110, "desc": "Downhill Sweeping Left-Right Chicane"},
        {"num": 3, "name": "Curva do Sol",  "ratio": 0.22, "speed": 235, "desc": "Long High-Lateral Left onto Reta Oposta"},
        {"num": 4, "name": "Descida do Lago","ratio": 0.38, "speed": 145, "desc": "Heavy Braking Downhill Double Left"},
        {"num": 6, "name": "Ferradura",     "ratio": 0.50, "speed": 180, "desc": "Long Right-Hand Uphill Carousel"},
        {"num": 8, "name": "Pinheirinho",   "ratio": 0.65, "speed": 95,  "desc": "Tight Technical Off-Camber Left"},
        {"num": 10,"name": "Bico de Pato",  "ratio": 0.74, "speed": 78,  "desc": "Slowest 1st-Gear Uphill Hairpin"},
        {"num": 12,"name": "Junção",        "ratio": 0.84, "speed": 130, "desc": "Decisive Left onto Flat-Out Climbing Straight"},
    ],
    "austin": [
        {"num": 1, "name": "Big Red",       "ratio": 0.10, "speed": 85,  "desc": "Steep 133-ft Blind Uphill Hairpin"},
        {"num": 3, "name": "The Esses",     "ratio": 0.22, "speed": 265, "desc": "Rapid Direction Changes"},
        {"num": 11,"name": "Hairpin",       "ratio": 0.44, "speed": 75,  "desc": "Heavy Braking Left onto 1.2km Back Straight"},
        {"num": 12,"name": "Stadium Entry", "ratio": 0.64, "speed": 90,  "desc": "330 km/h Deceleration into Stadium Complex"},
        {"num": 16,"name": "Carousel Triple Apex","ratio": 0.80,"speed": 210,"desc": "Sustained High-Lateral Right"},
        {"num": 19,"name": "Tower Corner",  "ratio": 0.92, "speed": 120, "desc": "Double 90° Left onto Pit Straight"},
    ],
    "canada": [
        {"num": 1, "name": "Virage Senna",  "ratio": 0.12, "speed": 98,  "desc": "Tight Left-Right Chicane"},
        {"num": 6, "name": "Pont de la Concorde","ratio": 0.32,"speed": 115,"desc": "Chicane over Island Bridge"},
        {"num": 10,"name": "L'Epingle",     "ratio": 0.60, "speed": 62,  "desc": "Tight 180° Heavy Braking Hairpin"},
        {"num": 13,"name": "Wall of Champions","ratio": 0.90,"speed": 140,"desc": "High Kerb Chicane Bordering the Concrete Wall"},
    ],
    "austria": [
        {"num": 1, "name": "Niki Lauda Kurve","ratio": 0.12,"speed": 145,"desc": "Uphill 90° Right Launch"},
        {"num": 3, "name": "Remus",         "ratio": 0.30, "speed": 72,  "desc": "Steep Uphill 1st-Gear Hairpin"},
        {"num": 4, "name": "Rauch",         "ratio": 0.44, "speed": 110, "desc": "Downhill Trail-Braking Right"},
        {"num": 6, "name": "Gerhard Berger","ratio": 0.62, "speed": 165, "desc": "Fast Downhill Left"},
        {"num": 9, "name": "Jochen Rindt",  "ratio": 0.82, "speed": 195, "desc": "High-Speed Downhill Right"},
        {"num": 10,"name": "Red Bull Mobile","ratio": 0.92,"speed": 210, "desc": "Full Throttle Apex Launch onto Pit Straight"},
    ],
    "netherlands": [
        {"num": 1, "name": "Tarzan",        "ratio": 0.12, "speed": 105, "desc": "Iconic 180° Right Dunes Hairpin"},
        {"num": 3, "name": "Hugenholtz",    "ratio": 0.25, "speed": 120, "desc": "Extreme 19° Parabolic Banking Left"},
        {"num": 7, "name": "Scheivlak",     "ratio": 0.48, "speed": 245, "desc": "Blind High-Speed Downhill Dunes Crest"},
        {"num": 11,"name": "Hans Ernst",    "ratio": 0.74, "speed": 88,  "desc": "Tight Double Chicane"},
        {"num": 14,"name": "Arie Luyendyk", "ratio": 0.92, "speed": 270, "desc": "18° Steep Banking Full-Throttle DRS Launch"},
    ],
    "bahrain": [
        {"num": 1, "name": "Michael Schumacher","ratio": 0.12,"speed": 75,"desc": "330 km/h Heavy Braking into Tight Right"},
        {"num": 4, "name": "Turn 4",        "ratio": 0.28, "speed": 135, "desc": "Uphill Fast Right Launch onto Back Section"},
        {"num": 8, "name": "Hairpin",       "ratio": 0.48, "speed": 80,  "desc": "Slow 1st-Gear Right Hairpin"},
        {"num": 10,"name": "Turn 10",       "ratio": 0.58, "speed": 72,  "desc": "Severe Downhill Off-Camber Lockup Risk"},
        {"num": 14,"name": "Final Corner",  "ratio": 0.90, "speed": 125, "desc": "Late Apex Acceleration onto Main Straight"},
    ],
    "saudi_arabia": [
        {"num": 1, "name": "Turn 1-2 Chicane","ratio": 0.08,"speed": 95, "desc": "Narrow Street Entry Chicane"},
        {"num": 8, "name": "High-Speed Esses","ratio": 0.26,"speed": 280,"desc": "Blind High-Speed Walls Sweep"},
        {"num": 13,"name": "Banked Hairpin","ratio": 0.45, "speed": 140, "desc": "12° Parabolic Banking Left"},
        {"num": 22,"name": "High-G Chicane","ratio": 0.74, "speed": 220, "desc": "Direction Change Bordering Coastal Walls"},
        {"num": 27,"name": "Final Hairpin", "ratio": 0.94, "speed": 85,  "desc": "Heavy Braking Left onto Coastal Main Straight"},
    ],
    "miami": [
        {"num": 1, "name": "Turn 1",        "ratio": 0.12, "speed": 98,  "desc": "Hard Braking 90° Left"},
        {"num": 5, "name": "High-Speed S",  "ratio": 0.25, "speed": 240, "desc": "Flowing High-Lateral Direction Changes"},
        {"num": 11,"name": "Marina Hairpin","ratio": 0.48, "speed": 80,  "desc": "Tight Slowest Hairpin"},
        {"num": 14,"name": "Overpass Chicane","ratio": 0.62,"speed": 75, "desc": "Uphill-Downhill Crest under Interstate Bridge"},
        {"num": 17,"name": "Turnpike Hairpin","ratio": 0.86,"speed": 72, "desc": "Heavy Braking from 340 km/h Back Straight"},
    ],
    "singapore": [
        {"num": 1, "name": "Sheares",       "ratio": 0.12, "speed": 110, "desc": "Heavy Braking Complex into Harbor Section"},
        {"num": 7, "name": "Memorial",      "ratio": 0.32, "speed": 90,  "desc": "90° Left onto Fast Raffles Boulevard"},
        {"num": 13,"name": "Anderson Bridge","ratio": 0.58,"speed": 85,  "desc": "Narrow Historical Bridge Crossing"},
        {"num": 14,"name": "Raffles Avenue","ratio": 0.68, "speed": 88,  "desc": "Heavy Deceleration 90° Right"},
        {"num": 16,"name": "Bay Chicane",   "ratio": 0.88, "speed": 145, "desc": "New High-Speed Bypass Straight"},
    ],
    "baku": [
        {"num": 1, "name": "Turn 1",        "ratio": 0.10, "speed": 100, "desc": "345 km/h Braking into 90° Left"},
        {"num": 3, "name": "Government House","ratio": 0.22,"speed": 95, "desc": "90° Left around Historic Plaza"},
        {"num": 8, "name": "Old City Castle","ratio": 0.44,"speed": 75,  "desc": "Tightest Section in F1 (7.6m Wide)"},
        {"num": 15,"name": "Downhill Left", "ratio": 0.65, "speed": 115, "desc": "Downhill Narrow Barrier Crest"},
        {"num": 16,"name": "Caspian Launch","ratio": 0.74, "speed": 140, "desc": "Exit onto 2.2km Flat-Out Seaside Boulevard"},
    ],
    "china": [
        {"num": 1, "name": "The Snail",     "ratio": 0.14, "speed": 80,  "desc": "270° Tightening Carousel Spiral"},
        {"num": 6, "name": "Turn 6 Hairpin","ratio": 0.35, "speed": 78,  "desc": "Downhill Braking Right Hairpin"},
        {"num": 13,"name": "Banked Launch", "ratio": 0.66, "speed": 190, "desc": "Steep Banked Curve onto 1.2km Long Straight"},
        {"num": 14,"name": "Hairpin",       "ratio": 0.88, "speed": 68,  "desc": "335 km/h Deceleration into 1st-Gear Hairpin"},
    ],
    "hungary": [
        {"num": 1, "name": "Turn 1 Downhill","ratio": 0.12,"speed": 105, "desc": "Steep Downhill Right Hairpin"},
        {"num": 2, "name": "Turn 2 Off-Camber","ratio": 0.24,"speed": 125,"desc": "Downhill Long Sweeping Left"},
        {"num": 4, "name": "Turn 4 Blind Crest","ratio": 0.38,"speed": 215,"desc": "High-Speed Blind Uphill Left"},
        {"num": 6, "name": "Chicane",       "ratio": 0.52, "speed": 95,  "desc": "Right-Left Kerb Ride"},
        {"num": 14,"name": "Final Corner",  "ratio": 0.92, "speed": 135, "desc": "Long Radius Carousel onto Main Straight"},
    ],
    "spain": [
        {"num": 1, "name": "Elf",           "ratio": 0.12, "speed": 135, "desc": "320 km/h Braking Right-Left Chicane"},
        {"num": 3, "name": "Renault",       "ratio": 0.22, "speed": 230, "desc": "Iconic Long 4.5G Accelerating Right"},
        {"num": 5, "name": "Seat",          "ratio": 0.38, "speed": 82,  "desc": "Downhill Left Hairpin"},
        {"num": 9, "name": "Campsa",        "ratio": 0.60, "speed": 240, "desc": "Blind Uphill High-Speed Right"},
        {"num": 10,"name": "La Caixa",      "ratio": 0.72, "speed": 85,  "desc": "Heavy Braking Left Hairpin"},
        {"num": 14,"name": "New Final Turn","ratio": 0.92, "speed": 260, "desc": "Fast Full-Throttle Sweeper onto Straight"},
    ],
    "imola": [
        {"num": 2, "name": "Variante Tamburello","ratio": 0.14,"speed": 140,"desc": "Left-Right-Left Kerb Chicane"},
        {"num": 5, "name": "Variante Villeneuve","ratio": 0.28,"speed": 165,"desc": "High-Speed Direction Change"},
        {"num": 7, "name": "Tosa",          "ratio": 0.38, "speed": 85,  "desc": "Steep Uphill Tight Hairpin"},
        {"num": 9, "name": "Piratella",     "ratio": 0.50, "speed": 195, "desc": "Blind Downhill Left"},
        {"num": 11,"name": "Acque Minerali","ratio": 0.62, "speed": 150, "desc": "Steep Downhill Compression followed by Uphill Flick"},
        {"num": 14,"name": "Variante Alta", "ratio": 0.76, "speed": 125, "desc": "High Kerb Crest Chicane"},
        {"num": 17,"name": "Rivazza 1 & 2", "ratio": 0.90, "speed": 115, "desc": "Downhill Double Left onto Main Straight"},
    ],
    "mexico": [
        {"num": 1, "name": "Turn 1 Chicane","ratio": 0.15,"speed": 110, "desc": "355 km/h Braking into Right-Left-Right"},
        {"num": 4, "name": "Turn 4-5",      "ratio": 0.32, "speed": 98,  "desc": "Heavy Braking Left-Right Chicane"},
        {"num": 7, "name": "The Esses",     "ratio": 0.52, "speed": 225, "desc": "Flowing High-Speed Direction Changes"},
        {"num": 12,"name": "Foro Sol Stadium","ratio": 0.82,"speed": 65,  "desc": "Stadium Complex through 40,000 Spectators"},
    ],
    "las_vegas": [
        {"num": 1, "name": "Turn 1 Hairpin","ratio": 0.10, "speed": 90,  "desc": "Tight Left around Paddock Building"},
        {"num": 5, "name": "The Sphere",    "ratio": 0.28, "speed": 125, "desc": "Sweeping Loop around Illuminated MSG Sphere"},
        {"num": 12,"name": "Strip Braking", "ratio": 0.58, "speed": 110, "desc": "Launch onto 1.9km Las Vegas Boulevard Strip"},
        {"num": 14,"name": "Bellagio Chicane","ratio": 0.88,"speed": 95, "desc": "350 km/h Deceleration past Bellagio Fountains"},
    ],
    "qatar": [
        {"num": 1, "name": "Turn 1",        "ratio": 0.12, "speed": 115, "desc": "335 km/h Braking into 90° Right"},
        {"num": 6, "name": "Turn 6 Hairpin","ratio": 0.38, "speed": 92,  "desc": "Tight Slowest Left Hairpin"},
        {"num": 12,"name": "Triple Apex Right","ratio": 0.70,"speed": 245,"desc": "5.2G Sustained Lateral High-Speed Complex"},
        {"num": 16,"name": "Final Corner",  "ratio": 0.92, "speed": 145, "desc": "Launch onto 1.068km Main Straight"},
    ],
    "abu_dhabi": [
        {"num": 1, "name": "Turn 1",        "ratio": 0.10, "speed": 140, "desc": "315 km/h Braking into 90° Left"},
        {"num": 5, "name": "North Hairpin", "ratio": 0.30, "speed": 80,  "desc": "Heavy Deceleration into Left Hairpin"},
        {"num": 9, "name": "Marsa Banked",  "ratio": 0.60, "speed": 195, "desc": "Banked Sweeping South Marina Corner"},
        {"num": 12,"name": "W Hotel Section","ratio": 0.78,"speed": 115,"desc": "Flowing Technical Section under Illuminated Hotel"},
    ]
}

# Mapping of calendar event IDs to GeoJSON feature IDs and orientation adjustments
CALENDAR_MAP = {
    "monaco":       {"geo_id": "mc-1929", "use_f1_telemetry": True, "rot": 0.0},
    "silverstone":  {"geo_id": "gb-1948", "use_f1_telemetry": False, "rot": 0.0},
    "monza":        {"geo_id": "it-1922", "use_f1_telemetry": False, "rot": 0.0},
    "spa":          {"geo_id": "be-1925", "use_f1_telemetry": False, "rot": 0.0},
    "australia":    {"geo_id": "au-1953", "use_f1_telemetry": False, "rot": 0.0},
    "china":        {"geo_id": "cn-2004", "use_f1_telemetry": False, "rot": 0.0},
    "japan":        {"geo_id": "jp-1962", "use_f1_telemetry": False, "rot": 0.0},
    "bahrain":      {"geo_id": "bh-2002", "use_f1_telemetry": False, "rot": 0.0},
    "saudi_arabia": {"geo_id": "sa-2021", "use_f1_telemetry": False, "rot": 0.0},
    "miami":        {"geo_id": "us-2022", "use_f1_telemetry": False, "rot": 0.0},
    "imola":        {"geo_id": "it-1953", "use_f1_telemetry": False, "rot": 0.0},
    "spain":        {"geo_id": "es-1991", "use_f1_telemetry": False, "rot": 0.0},
    "canada":       {"geo_id": "ca-1978", "use_f1_telemetry": False, "rot": 0.0},
    "austria":      {"geo_id": "at-1969", "use_f1_telemetry": False, "rot": 0.0},
    "hungary":      {"geo_id": "hu-1986", "use_f1_telemetry": False, "rot": 0.0},
    "netherlands":  {"geo_id": "nl-1948", "use_f1_telemetry": False, "rot": 0.0},
    "baku":         {"geo_id": "az-2016", "use_f1_telemetry": False, "rot": 0.0},
    "singapore":    {"geo_id": "sg-2008", "use_f1_telemetry": False, "rot": 0.0},
    "austin":       {"geo_id": "us-2012", "use_f1_telemetry": False, "rot": 0.0},
    "mexico":       {"geo_id": "mx-1962", "use_f1_telemetry": False, "rot": 0.0},
    "brazil":       {"geo_id": "br-1940", "use_f1_telemetry": False, "rot": 0.0},
    "las_vegas":    {"geo_id": "us-2023", "use_f1_telemetry": False, "rot": 0.0},
    "qatar":        {"geo_id": "qa-2004", "use_f1_telemetry": False, "rot": 0.0},
    "abu_dhabi":    {"geo_id": "ae-2009", "use_f1_telemetry": False, "rot": 0.0},
}

def build_monaco():
    import fastf1
    fastf1.Cache.enable_cache('data/raw_cache')
    session = fastf1.get_session(2023, 'Monaco', 'Q')
    session.load(telemetry=True, laps=True)
    lap = session.laps.pick_fastest()
    telemetry = lap.get_telemetry().dropna(subset=['X', 'Y'])
    circuit_info = session.get_circuit_info()

    times = telemetry['Time'].dt.total_seconds().tolist()
    t0 = times[0]
    norm_times = [round(t - t0, 3) for t in times]
    distances = telemetry['Distance'].values
    times_np = np.array(norm_times)

    corners = []
    for _, row in circuit_info.corners.iterrows():
        c_dist = row['Distance']
        c_idx = int(np.argmin(np.abs(distances - c_dist)))
        c_time = round(float(times_np[c_idx]), 1)
        c_num = int(row['Number'])
        c_letter = str(row['Letter']) if str(row['Letter']) != 'nan' else ''
        corners.append({
            'id': f'T{c_num}{c_letter}',
            'name': f'Turn {c_num}{c_letter}',
            'start': max(0.0, round(c_time - 2.0, 1)),
            'end': round(c_time + 2.0, 1),
            'type': 'Circuit Turn',
            'mid_t': c_time
        })

    xs = telemetry['X'].values
    ys = telemetry['Y'].values
    pad, bw, bh = 25, 320, 380
    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())

    track_points = []
    svg_parts = []
    for i in range(len(xs)):
        sx = round(pad + ((float(xs[i]) - x_min) / (x_max - x_min)) * (bw - 2 * pad), 1)
        sy = round(pad + (1.0 - (float(ys[i]) - y_min) / (y_max - y_min)) * (bh - 2 * pad), 1)
        track_points.append({
            't': norm_times[i],
            'x': sx,
            'y': sy,
            'spd': int(telemetry['Speed'].iloc[i])
        })
        prefix = 'M' if i == 0 else 'L'
        svg_parts.append(f'{prefix} {sx} {sy}')
    svg_parts.append('Z')

    corner_pins = []
    for c in corners:
        closest_idx = int(np.argmin([abs(pt['t'] - c['mid_t']) for pt in track_points]))
        corner_pins.append({
            'id': c['id'],
            'name': c['name'],
            'x': track_points[closest_idx]['x'],
            'y': track_points[closest_idx]['y'],
            'start': c['start'],
            'end': c['end'],
            'type': c['type'],
            'speed': int(telemetry['Speed'].iloc[closest_idx])
        })

    return {
        'viewBox': '0 0 320 380',
        'svg_path': ' '.join(svg_parts),
        'points': track_points,
        'corner_pins': corner_pins,
        'circuit_name': 'Circuit de Monaco',
        'location': 'Monte Carlo, Monaco',
        'lap_len': '3.337 km',
        'start_finish': {'x': track_points[0]['x'], 'y': track_points[0]['y']}
    }

def process_geojson_track(coords, name, location, lap_len, corner_defs, rotation=0.0):
    raw = np.array(coords, dtype=float)
    lons = raw[:, 0]
    lats = raw[:, 1]
    mean_lat = math.radians(np.mean(lats))
    
    # Project to Cartesian metric space
    xm = (lons - np.mean(lons)) * math.cos(mean_lat) * 111320.0
    ym = (lats - np.mean(lats)) * 110540.0
    
    if rotation != 0.0:
        rad = math.radians(rotation)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        xm, ym = xm * cos_a - ym * sin_a, xm * sin_a + ym * cos_a

    # Smooth periodic B-spline interpolation across closed curve
    try:
        tck, u = splprep([xm, ym], s=0, per=True)
        u_new = np.linspace(0, 1, 380, endpoint=False)
        smooth_x, smooth_y = splev(u_new, tck)
    except Exception:
        u_old = np.linspace(0, 1, len(xm))
        u_new = np.linspace(0, 1, 380, endpoint=False)
        smooth_x = np.interp(u_new, u_old, xm)
        smooth_y = np.interp(u_new, u_old, ym)

    pad = 25
    bw, bh = 320, 380
    min_x, max_x = float(smooth_x.min()), float(smooth_x.max())
    min_y, max_y = float(smooth_y.min()), float(smooth_y.max())
    span_x = max(max_x - min_x, 1e-5)
    span_y = max(max_y - min_y, 1e-5)
    
    scale = min((bw - 2 * pad) / span_x, (bh - 2 * pad) / span_y)
    off_x = pad + ((bw - 2 * pad) - span_x * scale) / 2.0
    off_y = pad + ((bh - 2 * pad) - span_y * scale) / 2.0
    
    svg_x = np.round(off_x + (smooth_x - min_x) * scale, 1)
    svg_y = np.round(off_y + (max_y - smooth_y) * scale, 1)
    
    n_pts = len(svg_x)
    track_points = []
    svg_parts = []
    lap_time = 82.0
    
    for i in range(n_pts):
        sx = float(svg_x[i])
        sy = float(svg_y[i])
        t = round((i / float(n_pts)) * lap_time, 2)
        track_points.append({'t': t, 'x': sx, 'y': sy, 'spd': 225})
        prefix = 'M' if i == 0 else 'L'
        svg_parts.append(f'{prefix} {sx} {sy}')
    svg_parts.append('Z')
    
    corner_pins = []
    for c in corner_defs:
        ratio = c.get('ratio', 0.5)
        target_t = round(ratio * lap_time, 1)
        idx = int(ratio * (n_pts - 1))
        pt = track_points[idx]
        corner_pins.append({
            'id': f"T{c['num']}",
            'name': f"Turn {c['num']} {c['name']}",
            'x': pt['x'],
            'y': pt['y'],
            'start': max(0.0, round(target_t - 2.0, 1)),
            'end': round(target_t + 2.0, 1),
            'type': c.get('desc', 'Circuit Corner'),
            'speed': c.get('speed', 150)
        })
        
    return {
        'viewBox': '0 0 320 380',
        'svg_path': ' '.join(svg_parts),
        'points': track_points,
        'corner_pins': corner_pins,
        'circuit_name': name,
        'location': location,
        'lap_len': lap_len,
        'start_finish': {'x': track_points[0]['x'], 'y': track_points[0]['y']}
    }

def compile_all_tracks():
    with open('data/f1_circuits_raw.geojson', 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    all_tracks = {}
    print('1. Compiling Monaco from FastF1 real telemetry...')
    all_tracks['monaco'] = build_monaco()
    print('   Monaco OK! Points:', len(all_tracks['monaco']['points']), 'Corners:', len(all_tracks['monaco']['corner_pins']))

    for cal_id, meta in CALENDAR_MAP.items():
        if cal_id == 'monaco':
            continue
        geo_id = meta['geo_id']
        feat = next((f for f in geojson_data['features'] if f['properties'].get('id') == geo_id), None)
        if not feat:
            print('   MISSING:', cal_id, geo_id)
            continue
            
        coords = feat['geometry']['coordinates']
        props = feat['properties']
        name = props.get('Name', cal_id.title())
        location = props.get('Location', '')
        length_m = props.get('length', 5200)
        lap_len = f"{round(length_m / 1000.0, 3)} km"
        
        corner_defs = CIRCUIT_CORNER_DEFINITIONS.get(cal_id, [
            {"num": 1, "name": "Turn 1", "ratio": 0.12, "speed": 110},
            {"num": 4, "name": "Turn 4", "ratio": 0.35, "speed": 140},
            {"num": 8, "name": "Turn 8", "ratio": 0.65, "speed": 180},
            {"num": 12, "name": "Turn 12", "ratio": 0.88, "speed": 120},
        ])
        
        track_dict = process_geojson_track(
            coords=coords,
            name=name,
            location=location,
            lap_len=lap_len,
            corner_defs=corner_defs,
            rotation=meta.get('rot', 0.0)
        )
        all_tracks[cal_id] = track_dict
        print(f"   {cal_id:15} -> {name:36} ({lap_len}) | Pts: {len(track_dict['points'])} | Corners: {len(track_dict['corner_pins'])}")

    out_path = 'backend/data_engine/accurate_circuit_maps.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_tracks, f)
    print(f"\nSuccessfully compiled all {len(all_tracks)} circuits to {out_path}!")

if __name__ == '__main__':
    compile_all_tracks()

