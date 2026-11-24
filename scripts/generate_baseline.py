import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from backend.vector_store.engine import VectorEngine
from backend.vector_store.db import VectorDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ROI_DIR = BASE_DIR / 'data' / 'generated_roi'
os.makedirs(ROI_DIR, exist_ok=True)

BASELINE_CATALOG = [
    {
        "filename": "baseline_baku_lockup_44.png",
        "session_id": "2021_Baku_GP",
        "driver": "44",
        "metadata": "2021 Baku GP Turn 1 restart: Severe front-left tire lockup with 100% brake pressure and brake-magic active.",
        "type": "lockup"
    },
    {
        "filename": "baseline_monaco_oversteer_14.png",
        "session_id": "2023_Monaco_GP",
        "driver": "14",
        "metadata": "2023 Monaco GP Turn 6 hairpin: Low grip surface transition causing mid-corner throttle hesitation and rear oversteer.",
        "type": "oversteer"
    },
    {
        "filename": "baseline_spa_tire_deg_55.png",
        "session_id": "2022_Spa_GP",
        "driver": "55",
        "metadata": "2022 Belgian GP Sector 2: Severe thermal degradation on soft compound leading to continuous micro-wheelspin on traction.",
        "type": "tire_deg"
    },
    {
        "filename": "baseline_silverstone_snap_4.png",
        "session_id": "2023_Silverstone_GP",
        "driver": "4",
        "metadata": "2023 British GP Copse Corner: High-speed aerodynamic balance shift under full throttle causing sudden lateral instability.",
        "type": "high_speed_snap"
    },
    {
        "filename": "baseline_nasa_battery_sag_cell3.png",
        "session_id": "NASA_Ames_B0005_Cycle84",
        "driver": "EV_Cell_3",
        "metadata": "NASA Ames B0005 Li-ion accelerated degradation: Severe voltage depression and 14C thermal gradient under 2C discharge.",
        "type": "ev_voltage_sag"
    },
    {
        "filename": "baseline_nasa_thermal_runaway_b0006.png",
        "session_id": "NASA_Ames_B0006_ThermalRunaway",
        "driver": "EV_Pack_0042",
        "metadata": "NASA Ames B0006 thermal runaway: Critical exothermic reaction exceeding 58C with steep negative dV/dt slope.",
        "type": "ev_thermal_runaway"
    },
    {
        "filename": "baseline_ev_cell_imbalance_mod4.png",
        "session_id": "Fleet_Unit_0109_Imbalance",
        "driver": "EV_Module_4",
        "metadata": "EV Fleet telemetry: 145mV inter-module delta indicating high internal resistance (R_int) in Module 4.",
        "type": "ev_cell_imbalance"
    },
    {
        "filename": "baseline_ev_regen_inrush_spike.png",
        "session_id": "Fleet_Unit_0088_RegenSpike",
        "driver": "EV_Pack_0088",
        "metadata": "Regenerative braking inrush: Severe 22A reverse current spike triggering pack overvoltage protection cutoff.",
        "type": "ev_regen_spike"
    }
]

def render_synthetic_crop(filepath: Path, anomaly_type: str):
    """
    Renders high-contrast white-on-black telemetry traces mimicking real telemetry slices.
    """
    time = np.linspace(0, 5, 200)
    fig, axes = plt.subplots(3, 1, figsize=(6, 5), sharex=True)
    fig.patch.set_facecolor('black')

    if anomaly_type == "lockup":
        # Speed drops sharply, Throttle is 0, Brake spikes to 100
        speed = 310 - (180 / (1 + np.exp(-3 * (time - 1.5))))
        throttle = np.where(time < 1.0, 80, 0)
        brake = np.where((time >= 1.0) & (time <= 3.2), 100, 0)
        channels = [('Speed (km/h)', speed), ('Throttle (%)', throttle), ('Brake (%)', brake)]
    elif anomaly_type == "ev_voltage_sag":
        # Voltage sags, Current high, Temperature rises
        voltage = 4.15 - (0.65 / (1 + np.exp(-2 * (time - 1.0))))
        current = np.where(time > 0.8, 45.0, 5.0)
        temp = 25.0 + 4.5 * time
        channels = [('Voltage (V)', voltage), ('Current (A)', current), ('Temperature (°C)', temp)]
    elif anomaly_type == "ev_thermal_runaway":
        # Exothermic temp surge, negative voltage collapse
        voltage = 3.9 - (0.9 / (1 + np.exp(-3 * (time - 2.0))))
        current = np.where(time < 2.5, 40.0, 10.0)
        temp = 28.0 + 8.5 * (time**1.3)
        channels = [('Voltage (V)', voltage), ('Current (A)', current), ('Temperature (°C)', temp)]
    elif anomaly_type == "ev_cell_imbalance":
        # Imbalance delta, lower pack voltage
        voltage = 3.65 - 0.25 * np.sin(time)
        current = 20.0 + 10.0 * np.cos(time)
        temp = 26.0 + 2.0 * time
        channels = [('Voltage (V)', voltage), ('Current (A)', current), ('Temperature (°C)', temp)]
    elif anomaly_type == "ev_regen_spike":
        # Sharp negative inrush current, overvoltage spike
        voltage = 3.8 + np.where((time >= 1.5) & (time <= 3.0), 0.45, 0.0)
        current = np.where((time >= 1.5) & (time <= 3.0), -22.0, 8.0)
        temp = 27.0 + 1.2 * time
        channels = [('Voltage (V)', voltage), ('Current (A)', current), ('Temperature (°C)', temp)]
    else:
        # Default oversteer / hesitation
        speed = 180 - 40 * np.sin(time)
        throttle = 40 + 30 * np.sin(2 * time)
        brake = np.where((time >= 0.5) & (time <= 1.8), 65, 0)
        channels = [('Speed (km/h)', speed), ('Throttle (%)', throttle), ('Brake (%)', brake)]

    for i, (label, data) in enumerate(channels):
        ax = axes[i]
        ax.plot(time, data, color='white', linewidth=1.5)
        ax.set_ylabel(label, color='white', fontsize=9)
        ax.set_facecolor('black')
        ax.tick_params(colors='white', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#333333')
        ax.grid(True, color='#222222', linestyle='--', alpha=0.7)

    axes[-1].set_xlabel('Time (s)', color='white', fontsize=9)
    plt.tight_layout()
    plt.savefig(filepath, facecolor='black', dpi=100)
    plt.close(fig)

def seed_database():
    logger.info("Initializing VectorEngine (CPU)...")
    engine = VectorEngine(device="cpu")
    db = VectorDB()

    logger.info(f"Existing FAISS vectors count: {db.index.ntotal}")

    for item in BASELINE_CATALOG:
        filepath = ROI_DIR / item["filename"]
        if not filepath.exists():
            render_synthetic_crop(filepath, item["type"])
            logger.info(f"Rendered baseline crop: {filepath.name}")

        embedding = engine.embed_artifact(str(filepath), item["metadata"])
        faiss_id = db.add_embedding(
            embedding=embedding,
            session_id=item["session_id"],
            driver=item["driver"],
            image_path=str(filepath),
            metadata=item["metadata"]
        )
        logger.info(f"Saved [{item['session_id']}] to FAISS ID: {faiss_id}")

    logger.info(f"Database successfully seeded! Total FAISS vectors: {db.index.ntotal}")

if __name__ == "__main__":
    seed_database()
