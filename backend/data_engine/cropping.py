import logging
import re
import threading
import uuid
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.core import config

logger = logging.getLogger(__name__)

ROI_DIR = config.ROI_DIR

# pyplot keeps global figure state and is not thread-safe; FastAPI runs sync
# endpoints in a threadpool, so all rendering is serialized through this lock.
_MPL_LOCK = threading.Lock()

_CHANNEL_COLORS = {
    "speed": "#00FF00",
    "throttle": "#00FFFF",
    "brake": "#FF2A4B",
    "gear": "#FFFF00",
    "rpm": "#FF00FF",
    "voltage": "#00FFFF",
    "current": "#FFFF00",
    "temperature": "#FF4500",
    "soc": "#00FF00",
    "cell_imbalance_mv": "#FF00FF",
}
_FALLBACK_COLORS = ["#00FF00", "#00FFFF", "#FF00FF", "#FFFF00", "#FF4500"]


def _make_filepath(session_id: str, label: str) -> Path:
    """Unique path per request so concurrent analyses cannot overwrite each other."""
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{session_id}_{label}")[:120].strip("_") or "roi"
    return ROI_DIR / f"{stem}_{uuid.uuid4().hex[:8]}_roi_crop.png"


def _slice_to_pandas(df):
    import polars as pl

    return df.to_pandas() if isinstance(df, pl.DataFrame) else df


def _render_crop(slice_data, channels, filepath: Path):
    """Renders a high-contrast, multi-axis waveform artifact for a VLM."""
    if not channels:
        raise ValueError("At least one telemetry channel is required")

    available = list(slice_data.columns)
    resolved = []
    for index, channel in enumerate(channels):
        matches = [column for column in available if column.lower() == channel.lower()]
        if matches:
            resolved.append((matches[0], _CHANNEL_COLORS.get(channel.lower(), _FALLBACK_COLORS[index % len(_FALLBACK_COLORS)])))

    if not resolved:
        raise ValueError(f"None of the requested channels {channels} exist in the telemetry slice")

    with _MPL_LOCK:
        fig, axes = plt.subplots(len(resolved), 1, figsize=(6, 2 * len(resolved)), sharex=True)
        if len(resolved) == 1:
            axes = [axes]

        x_values = slice_data["Time"] if "Time" in slice_data.columns else np.arange(len(slice_data))

        for axis, (column, color) in zip(axes, resolved):
            axis.plot(x_values, slice_data[column], color=color, linewidth=1.6)
            axis.set_ylabel(column, color=color, fontweight="bold", fontsize=9)
            axis.tick_params(axis="y", colors="white", labelsize=8)
            axis.tick_params(axis="x", colors="white", labelsize=8)
            axis.set_facecolor("black")
            for spine in axis.spines.values():
                spine.set_color("#333333")
            axis.grid(True, color="#222222", linestyle="--", alpha=0.7)

        axes[-1].set_xlabel("Time (s)", color="white", fontsize=9)
        fig.patch.set_facecolor("black")
        plt.tight_layout()
        try:
            plt.savefig(filepath, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        finally:
            plt.close(fig)

    logger.info("ROI crop saved to %s", filepath)
    return filepath


class ROICropper:
    @staticmethod
    def generate_roi_crop(session, driver: str, start_time, end_time, channels: list, session_id: str):
        """Slices a FastF1 session's car data and renders the ROI artifact."""
        try:
            car_data = session.car_data[driver]
        except KeyError:
            logger.error("Driver %s not found in session car data.", driver)
            raise ValueError(f"Driver {driver} not found")

        try:
            slice_data = car_data.slice_by_time(start_time, end_time)
        except Exception as exc:
            logger.error("Failed to slice data by time: %s", exc)
            raise

        if slice_data is None or slice_data.empty:
            raise ValueError("Empty ROI bounds")

        return _render_crop(slice_data, channels, _make_filepath(session_id, driver))

    @staticmethod
    def generate_dataframe_roi_crop(df, start_time: float, end_time: float, channels: list, session_id: str):
        """Slices numeric-time DataFrame telemetry and renders the ROI artifact."""
        import polars as pl

        if isinstance(df, pl.DataFrame):
            slice_data = df.filter(
                (pl.col("Time") >= start_time) & (pl.col("Time") <= end_time)
            ).to_pandas()
        else:
            slice_data = df[(df["Time"] >= start_time) & (df["Time"] <= end_time)]

        if slice_data.empty:
            raise ValueError("Empty ROI bounds")

        return _render_crop(slice_data, channels, _make_filepath(session_id, "f1"))

    @staticmethod
    def generate_ev_roi_crop(df, start_time: float, end_time: float, channels: list, session_id: str):
        """Slices EV battery telemetry and renders the ROI artifact."""
        import polars as pl

        if isinstance(df, pl.DataFrame):
            slice_data = df.filter(
                (pl.col("Time") >= start_time) & (pl.col("Time") <= end_time)
            ).to_pandas()
        else:
            slice_data = df[(df["Time"] >= start_time) & (df["Time"] <= end_time)]

        if slice_data.empty:
            raise ValueError("Empty ROI bounds")

        return _render_crop(slice_data, channels, _make_filepath(session_id, "ev"))
