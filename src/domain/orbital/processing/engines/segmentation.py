import polars as pl
import numpy as np
from typing import Dict, Any
from src.shared.enums.dataset_enums import DatasetRole


class OrbitalSegmenter:
    """
    Segments satellite timelines by detecting maneuvers and data gaps.
    Splits into physically consistent orbital regimes.
    """

    SECONDS_IN_DAY = 86400.0

    def __init__(self, segmentation_config: Dict[str, Dict[str, Any]], earth_mu: float):
        self.config = segmentation_config
        self.earth_mu = earth_mu

    def process(self, df: pl.DataFrame, dataset_role: DatasetRole) -> pl.DataFrame:
        """Segments data based on temporal gaps and orbital energy shifts."""
        role_cfg = self.config[dataset_role.value]

        max_gap_hours = role_cfg["max_gap_hours"]
        maneuver_tol = role_cfg["maneuver_delta_a_km"]

        df = df.sort(["norad_cat_id", "epoch_dt"])

        df = df.with_columns(
            pl.col("epoch_dt").diff().dt.total_hours()
            .over("norad_cat_id").fill_null(0).alias("delta_hours"))

        # 2. Re-calc Semi-Major Axis (Energy Metric)
        # -------------------------------------------------------------------------
        # we ignore the raw 'SEMIMAJOR_AXIS' col from Space-Track and re-calculate
        # it from mean motion to ensure internal consistency:
        #
        # - Native TLEs don't actually contain SMA anyway (it's always derived).
        # - Prevents gravity constant mismatches. Ensures the SMA perfectly aligns
        #   with our SGP4 engine's specific `earth_mu`.
        # - Acts as a safe fallback if the upstream provider leaves derived cols empty.
        # -------------------------------------------------------------------------
        mean_motion_rad_s = pl.col("mean_motion") * (2 * np.pi / self.SECONDS_IN_DAY)

        df = df.with_columns(
            pl.when(mean_motion_rad_s > 0)
            .then(((self.earth_mu / (mean_motion_rad_s ** 2)) ** (1 / 3)))
            .otherwise(None)
            .alias("semimajor_axis"))

        df = df.with_columns(
            pl.col("semimajor_axis").diff().over("norad_cat_id").fill_null(0).alias("delta_a"))

        is_new_segment = (
                (pl.col("delta_hours") > max_gap_hours) |
                (pl.col("delta_a") > maneuver_tol) |
                (pl.col("norad_cat_id") != pl.col("norad_cat_id").shift(1))
        ).fill_null(True)

        df = df.with_columns(
            is_new_segment.cast(pl.Int32).cum_sum().alias("global_segment_index"))

        df = df.with_columns(
            pl.concat_str([
                pl.col("norad_cat_id").cast(pl.Utf8),
                pl.lit("_Seg"),
                pl.col("global_segment_index").cast(pl.Utf8)
            ]).alias("segment_id"))

        df = df.drop(["delta_hours", "delta_a", "global_segment_index"])

        return df