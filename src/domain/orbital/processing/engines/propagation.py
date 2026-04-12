import polars as pl
from datetime import timedelta
from typing import Dict, Any, List
from structlog.stdlib import BoundLogger
from src.shared.enums.dataset_enums import DatasetRole

try:
    from orbital_plugin import propagate_state_vectors
except ImportError:
    def propagate_state_vectors(*args):
        raise ImportError("Rust plugin not found. Run 'maturin develop --release'")

_STATE_COLS = ["sgp4_error", "pos_x", "pos_y", "pos_z", "vel_x", "vel_y", "vel_z"]

class SGP4Propagator:
    """
    Normalizes orbital data to regular time grid via SGP4 propagation.
    Fully vectorized using Rust Polars plugin (GIL-free).
    """

    def __init__(self, logger: BoundLogger, config: Dict[str, Dict[str, Any]], static_columns_to_keep: List[str]):
        self.logger = logger
        self.config = config
        self.static_cols_to_keep = static_columns_to_keep

    def process(self, df: pl.DataFrame, dataset_role: DatasetRole) -> pl.DataFrame:
        """Generates regular time grid for each segment and propagates state vectors."""
        role_cfg = self.config[dataset_role.value]
        grid_hours = role_cfg["grid_interval_hours"]
        grid_interval = f"{grid_hours}h"

        df = self._compute_measured_state_vectors(df)

        result_frames: list[pl.DataFrame] = []

        for seg_df in df.partition_by("segment_id", maintain_order=False):
            seg_id    = seg_df["segment_id"][0]
            start_dt  = seg_df["epoch_dt"].min()
            end_dt    = seg_df["epoch_dt"].max()

            self.logger.debug(
                "sgp4_segment_processing_started",
                segment_id=seg_id,
                grid_interval_hours=grid_hours,
                real_tle_points=seg_df.height,
            )

            start_grid = start_dt.replace(minute=0, second=0, microsecond=0)
            start_grid = start_grid - timedelta(hours=start_grid.hour % grid_hours)

            grid_times = pl.datetime_range(
                start=start_grid,
                end=end_dt,
                interval=grid_interval,
                eager=True,
            ).alias("epoch_dt")

            df_grid = pl.DataFrame({"epoch_dt": grid_times})

            seg_df_for_join = seg_df.with_columns(
                pl.col("epoch_dt").alias("source_epoch")
            )

            df_merged = (
                df_grid
                .sort("epoch_dt")
                .join_asof(
                    seg_df_for_join.sort("epoch_dt"),
                    on="epoch_dt",
                    strategy="backward",
                )
                .drop_nulls(subset=["tle_line1"])
            )

            if df_merged.is_empty():
                self.logger.debug(
                    "sgp4_no_synthetic_rows_generated",
                    segment_id=seg_id,
                    reason="no_valid_reference_tle_after_asof_join",
                )
                result_frames.append(seg_df)
                continue

            df_prop = self._propagate(df_merged)

            df_prop = df_prop.with_columns([
                pl.lit(1).cast(pl.Int32).alias("is_synthetic"),
                pl.lit("propagated").alias("source"),

                ((pl.col("epoch_dt") - pl.col("source_epoch"))
                 .dt.total_milliseconds() / 60000.0).alias("propagation_minutes"),

                pl.col("epoch_dt").dt.strftime("%Y-%m-%dT%H:%M:%S").alias("epoch"),

                pl.col("mean_motion").alias("ref_mean_motion"),
                pl.col("eccentricity").alias("ref_eccentricity"),
                pl.col("inclination").alias("ref_inclination"),
                pl.col("ra_of_asc_node").alias("ref_ra_of_asc_node"),
                pl.col("arg_of_pericenter").alias("ref_arg_of_pericenter"),
                pl.col("mean_anomaly").alias("ref_mean_anomaly"),
                pl.col("bstar").alias("ref_bstar"),
                pl.col("semimajor_axis").alias("ref_semimajor_axis"),
                pl.col("mean_motion_dot").alias("ref_mean_motion_dot"),
                pl.col("mean_motion_ddot").alias("ref_mean_motion_ddot"),
            ])

            null_ref = pl.lit(None).cast(pl.Float64)
            df_real = seg_df.with_columns([
                pl.lit(0).cast(pl.Int32).alias("is_synthetic"),
                pl.lit("measured").alias("source"),
                pl.col("epoch_dt").alias("source_epoch"),
                pl.lit(0.0).alias("propagation_minutes"),
                null_ref.alias("ref_mean_motion"),
                null_ref.alias("ref_eccentricity"),
                null_ref.alias("ref_inclination"),
                null_ref.alias("ref_ra_of_asc_node"),
                null_ref.alias("ref_arg_of_pericenter"),
                null_ref.alias("ref_mean_anomaly"),
                null_ref.alias("ref_bstar"),
                null_ref.alias("ref_semimajor_axis"),
                null_ref.alias("ref_mean_motion_dot"),
                null_ref.alias("ref_mean_motion_ddot"),
            ])

            common_cols = [c for c in df_real.columns if c in df_prop.columns]
            df_combined = (
                pl.concat(
                    [df_real.select(common_cols), df_prop.select(common_cols)],
                    how="vertical",
                )
                .sort(["epoch_dt", "is_synthetic"])
                .unique(subset=["norad_cat_id", "epoch_dt"], keep="first")
            )

            df_syn   = df_combined.filter(pl.col("is_synthetic") == 1)
            produced = df_prop.height
            kept     = df_syn.height
            dropped  = produced - kept

            if dropped > 0:
                self.logger.debug(
                    "sgp4_synthetic_rows_dropped_due_to_real_overlap",
                    segment_id=seg_id,
                    produced=produced,
                    kept=kept,
                    dropped=dropped,
                )

            self.logger.debug(
                "sgp4_synthetic_rows_generated",
                segment_id=seg_id,
                synthetic_rows=produced,
                grid_points=df_grid.height,
                real_tle_points=seg_df.height,
                grid_interval=grid_hours,
            )

            result_frames.append(df_combined)

        if not result_frames:
            return pl.DataFrame()

        return pl.concat(result_frames)

    def _propagate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drops stale state columns, runs Rust SGP4 plugin, unnests result."""
        return (
            df
            .drop([c for c in _STATE_COLS if c in df.columns])
            .with_columns(
                propagate_state_vectors(
                    pl.col("tle_line1"),
                    pl.col("tle_line2"),
                    pl.col("epoch_dt"),
                ).alias("state_data")
            )
            .unnest("state_data")
        )

    def _compute_measured_state_vectors(self, df: pl.DataFrame) -> pl.DataFrame:
        """Computes pos/vel for measured TLE rows (dt=0) via Rust plugin."""
        return self._propagate(df)