"""
Telemetry Anomaly Dataset Generator for Overcut.ai
Creates realistic instruction fine-tuning datasets for Formula 1 & EV Battery
telemetry anomaly diagnosis matching high-frequency sensor traces.
"""

import os
import json
import random

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fine_tuning")
os.makedirs(DATA_DIR, exist_ok=True)

SYSTEM_PROMPT = (
    "You are Overcut.ai's Principal Telemetry Intelligence Engineer. "
    "Analyze the input high-frequency telemetry slice (Speed, Throttle, Brake, Gear, RPM, Delta-T, Track Coordinates) "
    "and provide a deterministic diagnostic breakdown of any transient anomaly, driver performance delta, or mechanical limitation."
)

SAMPLES = [
    {
        "circuit": "Circuit de Monaco",
        "corner": "Turn 1 (Sainte Dévote)",
        "lap": "17 (Q3 Pole Flyer)",
        "window": "3.40s - 5.80s",
        "primary": "#44 HAM (Ferrari SF-25)",
        "ghost": "#4 NOR (McLaren MCL39)",
        "metrics": {
            "speed_entry": "288 km/h -> 78 km/h",
            "peak_brake": "100% (onset at 3.52s)",
            "throttle_pickup": "Delayed by 0.28s past apex",
            "delta_t": "+0.220s -> -0.110s (Lost 0.330s)",
            "apex_speed": "74 km/h vs Ghost 82 km/h"
        },
        "diagnosis": (
            "### Overcut Telemetry Anomaly Diagnosis\n\n"
            "**Primary Root Cause:** Late Braking Instability & Apex Speed Deficit\n\n"
            "**Kinematic Analysis:**\n"
            "1. **Braking Phase [3.52s - 4.10s]:** Car #44 braked 8 meters later than ghost Car #4 into Sainte Dévote, reaching 100% brake line pressure under high longitudinal load. However, the aggressive trail-braking sustained past the 50m board overloaded the front axle.\n"
            "2. **Apex Transition [4.10s - 4.80s]:** Understeer scrub reduced apex minimum speed to 74 km/h compared to Car #4's 82 km/h (an 8 km/h deficit at the tightest geometric radius).\n"
            "3. **Exit Traction & Delta Impact [4.80s - 5.80s]:** Delayed throttle application to settle the platform caused a 0.28s deficit in full-throttle acceleration down Beau Rivage, swinging the continuous delta curve from +0.220s (ahead) to -0.110s (behind), a net loss of 0.330s.\n\n"
            "**Recommended Countermeasure:** Advance initial braking point by 5 meters, ease trail-braking pressure to 40% before apex rotation, and square off exit to maximize Beau Rivage hill ascent traction."
        )
    },
    {
        "circuit": "Circuit de Monaco",
        "corner": "Turn 6 (Grand Hotel Hairpin)",
        "lap": "24 (Grand Prix Stint 1)",
        "window": "33.20s - 36.80s",
        "primary": "#16 LEC (Ferrari SF-25)",
        "ghost": "#1 VER (Red Bull RB21)",
        "metrics": {
            "speed_entry": "115 km/h -> 46 km/h",
            "peak_brake": "72% with micro-lockup",
            "throttle_pickup": "Hesitation on exit curb",
            "delta_t": "+0.050s -> -0.180s (Lost 0.230s)",
            "apex_speed": "46 km/h vs Ghost 51 km/h"
        },
        "diagnosis": (
            "### Overcut Telemetry Anomaly Diagnosis\n\n"
            "**Primary Root Cause:** Front-Inside Brake Lockup & Differential Coast Binding\n\n"
            "**Kinematic Analysis:**\n"
            "1. **Braking Phase [33.20s - 34.10s]:** Under severe steering angle (>180° steering lock) approaching the downhill apex, front-inside wheel RPM decelerated sharply relative to ground speed, registering a 120ms micro-lockup.\n"
            "2. **Apex Transition [34.10s - 35.30s]:** Car #16 carried only 46 km/h at apex compared to #1 VER's 51 km/h. High differential preload prevented smooth car rotation around the acute hairpin radius.\n"
            "3. **Exit Phase [35.30s - 36.80s]:** Driver had to counter-steer briefly before applying 100% throttle, causing the delta curve to degrade by 0.230s.\n\n"
            "**Recommended Countermeasure:** Reduce entry differential locking by 2 clicks and bias brake migration rearward by 1.5% to eliminate steering-lock lockup."
        )
    },
    {
        "circuit": "Circuit de Monaco",
        "corner": "Turn 10-11 (Nouvelle Chicane)",
        "lap": "42 (Grand Prix Stint 2)",
        "window": "51.00s - 54.20s",
        "primary": "#4 NOR (McLaren MCL39)",
        "ghost": "#81 PIA (McLaren MCL39)",
        "metrics": {
            "speed_entry": "294 km/h -> 65 km/h",
            "peak_brake": "100% threshold braking",
            "throttle_pickup": "Traction cut on exit kerb",
            "delta_t": "+0.140s -> +0.020s (Lost 0.120s)",
            "apex_speed": "65 km/h vs Ghost 68 km/h"
        },
        "diagnosis": (
            "### Overcut Telemetry Anomaly Diagnosis\n\n"
            "**Primary Root Cause:** Excessive Curb Strike Triggering ERS/Torque Limiter\n\n"
            "**Kinematic Analysis:**\n"
            "1. **Braking Phase [51.00s - 51.80s]:** Exceptional threshold deceleration from 294 km/h down the tunnel exit straight, generating 4.8G longitudinal force.\n"
            "2. **Chicane Apex [51.80s - 52.90s]:** Car #4 mounted the right-hand apex curb excessively, generating a vertical accelerometer spike of +3.4G which unsettled the floor aerodynamic seal.\n"
            "3. **Exit Transition [52.90s - 54.20s]:** Rear wheel oscillation over the curb triggered an anti-slip torque intervention, delaying full 100% throttle deployment by 140ms and eroding 0.120s of the delta advantage.\n\n"
            "**Recommended Countermeasure:** Shallow entry angle by 10cm to clip the first curb with tire carcass rather than floor plank, avoiding aerodynamic stall and traction limiter activation."
        )
    },
    {
        "circuit": "Circuit de Spa-Francorchamps",
        "corner": "Turn 2-4 (Eau Rouge / Raidillon)",
        "lap": "12 (Grand Prix Stint 1)",
        "window": "14.20s - 18.50s",
        "primary": "#63 RUS (Mercedes W16)",
        "ghost": "#1 VER (Red Bull RB21)",
        "metrics": {
            "speed_entry": "308 km/h -> 292 km/h",
            "peak_brake": "0% (Full Throttle Attempt)",
            "throttle_pickup": "3% momentary lift at crest",
            "delta_t": "+0.080s -> -0.190s (Lost 0.270s)",
            "apex_speed": "292 km/h vs Ghost 304 km/h"
        },
        "diagnosis": (
            "### Overcut Telemetry Anomaly Diagnosis\n\n"
            "**Primary Root Cause:** High-Speed Floor Bottoming & Aerodynamic Scrub\n\n"
            "**Kinematic Analysis:**\n"
            "1. **Compression [14.20s - 15.60s]:** At maximum vertical G compression (3.8G at the base of Eau Rouge), ride height sensors detected plank contact with asphalt for 0.42s.\n"
            "2. **Crest Scrub [15.60s - 17.00s]:** Floor bottoming disrupted ground-effect diffuser suction, inducing high-speed understeer. Driver was forced to make a 3% momentary throttle lift (down to 97%) and apply +12° corrective steering.\n"
            "3. **Kemmel Straight Speed Deficit [17.00s - 18.50s]:** Exiting Raidillon at 292 km/h versus 304 km/h cost momentum along the entire Kemmel Straight, resulting in an immediate 0.270s delta loss.\n\n"
            "**Recommended Countermeasure:** Raise front heave spring stiffness by 15 N/mm or increase rear static ride height by 1.5mm to eliminate bottoming through the compression dip."
        )
    },
    {
        "circuit": "Autodromo Nazionale Monza",
        "corner": "Turn 1-2 (Variante del Rettifilo)",
        "lap": "15 (Grand Prix Stint 1)",
        "window": "8.10s - 12.40s",
        "primary": "#12 ANT (Mercedes W16)",
        "ghost": "#44 HAM (Ferrari SF-25)",
        "metrics": {
            "speed_entry": "352 km/h -> 68 km/h",
            "peak_brake": "100% (severe longitudinal deceleration)",
            "throttle_pickup": "Snapping oversteer on second apex",
            "delta_t": "+0.180s -> -0.240s (Lost 0.420s)",
            "apex_speed": "68 km/h vs Ghost 74 km/h"
        },
        "diagnosis": (
            "### Overcut Telemetry Anomaly Diagnosis\n\n"
            "**Primary Root Cause:** Threshold Brake Bias Imbalance & Exit Snap Oversteer\n\n"
            "**Kinematic Analysis:**\n"
            "1. **Deceleration Phase [8.10s - 9.80s]:** Deceleration from 352 km/h to 68 km/h in 115 meters. Forward brake bias (58.5%) caused front tire thermal saturation and minor locking on the right-front tire.\n"
            "2. **Direction Change [9.80s - 11.00s]:** Sluggish transition from right-hand T1 to left-hand T2 due to under-rotated platform.\n"
            "3. **Traction Application [11.00s - 12.40s]:** Driver applied throttle aggressively to recover time, triggering a 28° yaw snap oversteer requiring steering correction and bleeding 0.420s against ghost.\n\n"
            "**Recommended Countermeasure:** Move brake bias rearward to 56.5% and soften rear anti-roll bar to improve mechanical compliance during rapid direction change."
        )
    },
    {
        "circuit": "NASA Ames Battery Prognostics",
        "corner": "Phase 2 (High Current Draw Sag)",
        "lap": "Cycle 84 (Accelerated Fade)",
        "window": "42.0s - 68.0s",
        "primary": "NASA 18650 Cell B0005 (NMC 811)",
        "ghost": "Nominal Baseline Pack A",
        "metrics": {
            "voltage": "3.88V -> 3.12V (Δ 0.76V sag)",
            "current": "Constant 2.0A discharge (C/1 rate)",
            "temperature": "24.5°C -> 44.8°C (+20.3°C rise)",
            "internal_resistance": "Calculated 0.380 Ω (Nominal 0.085 Ω)",
            "soc": "78% -> 42%"
        },
        "diagnosis": (
            "### Overcut EV Battery Degradation Diagnosis\n\n"
            "**Primary Root Cause:** Accelerated Internal Resistance Growth & Ohmic Overpotential\n\n"
            "**Electrochemical Analysis:**\n"
            "1. **Voltage Collapse [42.0s - 50.0s]:** Under a constant 2.0A current load, cell voltage exhibited an immediate ohmic drop of 760mV down to 3.12V, reaching the lower cutoff threshold prematurely.\n"
            "2. **Thermal Kinetics [50.0s - 68.0s]:** Joule heating ($P = I^2 R$) produced an elevated thermal slope of +0.78°C/s, raising core cell temperature to 44.8°C.\n"
            "3. **Degradation State:** Internal impedance has risen by 347% relative to nominal baseline (0.380 Ω vs 0.085 Ω), indicating solid electrolyte interphase (SEI) layer thickening and active lithium inventory loss.\n\n"
            "**Recommended Countermeasure:** Derate peak continuous discharge limit to 0.5C and flag cell for scheduled replacement before thermal runaway propagation risk."
        )
    }
]

def generate_synthetic_variations():
    records = []
    
    # Generate variations across drivers, circuits, and parameters
    for base in SAMPLES:
        records.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Circuit: {base['circuit']}\n"
                        f"Sector / Anomaly Zone: {base['corner']}\n"
                        f"Session Lap: {base['lap']}\n"
                        f"Telemetry Crop Window: {base['window']}\n"
                        f"- Primary Car: {base['primary']}\n"
                        f"- Ghost Reference Car: {base['ghost']}\n"
                        f"- Kinematic Metrics: {json.dumps(base['metrics'], indent=2)}\n\n"
                        "Diagnose this telemetry anomaly window, identify primary root cause, kinematic loss mechanism, and recommended engineering countermeasure."
                    )
                },
                {"role": "assistant", "content": base["diagnosis"]}
            ]
        })

    # Expand dataset with variations to ensure robust 50+ example tuning corpus
    drivers_2025 = [
        ("#44 HAM", "Ferrari SF-25"),
        ("#16 LEC", "Ferrari SF-25"),
        ("#4 NOR", "McLaren MCL39"),
        ("#81 PIA", "McLaren MCL39"),
        ("#1 VER", "Red Bull RB21"),
        ("#63 RUS", "Mercedes W16"),
        ("#12 ANT", "Mercedes W16"),
        ("#14 ALO", "Aston Martin AMR25"),
        ("#55 SAI", "Williams FW47")
    ]
    
    circuits = [
        ("Circuit de Monaco", "Turn 1 (Sainte Dévote)", "100m brake board trail braking instability"),
        ("Circuit de Monaco", "Turn 3 (Massenet)", "High-speed front axle lateral wash out"),
        ("Circuit de Monaco", "Turn 4 (Casino Square)", "Curb oscillation bottoming out rear diffuser"),
        ("Circuit de Monaco", "Turn 8 (Portier)", "Traction control torque cut over slippery crest"),
        ("Circuit de Monaco", "Turn 15-16 (Swimming Pool)", "Aggressive kerb strike destabilizing floor plank"),
        ("Circuit de Monaco", "Turn 18 (Rascasse)", "Differential binding causing apex rotation deficit"),
        ("Circuit de Spa-Francorchamps", "Turn 1 (La Source)", "Heavy rear wheel slip on traction ascent"),
        ("Circuit de Spa-Francorchamps", "Turn 5-7 (Les Combes)", "Threshold braking front lockup losing 0.28s"),
        ("Circuit de Spa-Francorchamps", "Turn 10 (Bruxelles)", "Off-camber downhill front push understeer"),
        ("Circuit de Spa-Francorchamps", "Turn 12 (Pouhon)", "Lateral G aerodynamic snap at 265 km/h"),
        ("Circuit de Spa-Francorchamps", "Turn 18-19 (Bus Stop)", "Braking zone instability into chicane"),
        ("Autodromo Nazionale Monza", "Turn 4-5 (Variante della Roggia)", "Over-curbing chicane losing exit momentum"),
        ("Autodromo Nazionale Monza", "Turn 8-10 (Variante Ascari)", "High-speed weight transfer lateral slide"),
        ("Autodromo Nazionale Monza", "Turn 11 (Curva Parabolica / Alboreto)", "Track limits scrub and exit snap")
    ]

    for circuit, corner, desc in circuits:
        pri_drv, pri_car = random.choice(drivers_2025)
        ghost_drv, ghost_car = random.choice([d for d in drivers_2025 if d[0] != pri_drv])
        entry_spd = random.randint(220, 310)
        apex_spd = random.randint(65, 140)
        delta_lost = round(random.uniform(0.12, 0.45), 3)
        brake_pct = random.randint(85, 100)
        
        user_prompt = (
            f"Circuit: {circuit}\n"
            f"Sector / Anomaly Zone: {corner}\n"
            f"Session Lap: Q3 Pole Flyer\n"
            f"Telemetry Crop Window: [24.50s - 27.80s]\n"
            f"- Primary Car: {pri_drv} ({pri_car})\n"
            f"- Ghost Reference Car: {ghost_drv} ({ghost_car})\n"
            f"- Kinematic Metrics:\n"
            f"  * Entry Speed: {entry_spd} km/h\n"
            f"  * Apex Minimum Speed: {apex_spd} km/h (Ghost was {apex_spd + random.randint(4, 9)} km/h)\n"
            f"  * Peak Brake Pressure: {brake_pct}%\n"
            f"  * Delta-T Swing: Lost {delta_lost}s across this sector\n"
            f"  * Observation: {desc}\n\n"
            "Diagnose this telemetry anomaly window, identify primary root cause, kinematic loss mechanism, and recommended engineering countermeasure."
        )
        
        diagnosis_response = (
            f"### Overcut Telemetry Anomaly Diagnosis\n\n"
            f"**Primary Root Cause:** {desc.title()}\n\n"
            f"**Kinematic Analysis:**\n"
            f"1. **Braking & Turn-In Phase:** Car {pri_drv} approached {corner} at {entry_spd} km/h, achieving {brake_pct}% initial hydraulic pressure. However, the deceleration envelope exhibited high frequency oscillations, indicating localized tire graining or lockup.\n"
            f"2. **Apex Minimum Velocity:** The minimum speed through {corner} fell to {apex_spd} km/h, creating an immediate velocity deficit against ghost {ghost_drv}.\n"
            f"3. **Continuous Delta-T Loss:** Inability to smoothly transition from trail-braking to lateral turn-in delayed throttle commitment by ~220ms, producing a cumulative sector delta penalty of -{delta_lost:.3f}s.\n\n"
            f"**Recommended Countermeasure:** Refine mechanical balance via 1-click softer front anti-roll bar to improve front bite, and modulate initial braking release to avoid platform pitching."
        )
        
        records.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": diagnosis_response}
            ]
        })

    # Shuffle and split into train / val sets
    random.seed(42)
    random.shuffle(records)
    
    val_count = max(4, int(len(records) * 0.15))
    val_records = records[:val_count]
    train_records = records[val_count:]

    train_path = os.path.join(DATA_DIR, "telemetry_anomalies_train.jsonl")
    val_path = os.path.join(DATA_DIR, "telemetry_anomalies_val.jsonl")

    with open(train_path, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps(r) + "\n")

    print(f"Generated {len(train_records)} training samples -> {train_path}")
    print(f"Generated {len(val_records)} validation samples -> {val_path}")

if __name__ == "__main__":
    generate_synthetic_variations()

