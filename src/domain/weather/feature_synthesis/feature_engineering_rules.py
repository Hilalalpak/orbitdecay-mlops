"""
Creates space weather features from raw data. Calculates rolling averages, lag features,
and physics-based indicators using Polars. Basically turns messy weather data into
something our ML models can actually understand.
"""
import polars as pl
from structlog.stdlib import BoundLogger


class EnvironmentFeatureEngineer:
    """
    Takes raw space weather data and creates useful features.
    Handles flux, KP index, and sunspot data to generate lagged variables
    and rolling averages that our models can actually use.
    """

    def __init__(self, logger: BoundLogger) -> None:
        self.logger = logger

    def apply_features(self, flux_df: pl.DataFrame, kp_df: pl.DataFrame, sunspot_df: pl.DataFrame) -> pl.DataFrame:
        """
        Runs the full feature engineering pipeline.
        Creates lagged physical features and uses Asof Join to prevent data leakage.
        Basically makes sure our models don't cheat by seeing future data.
        """

        # 1. FLUX (Daily): Clip anomalies & add Thermal Inertia
        if not flux_df.is_empty():
            flux_df = flux_df.sort("date").with_columns([
                # Physical Ceiling (Clipping anomalies like 1600 sfu)
                pl.col("observed_flux").clip(upper_bound=400.0).alias("observed_flux")
            ]).with_columns([
                # Moving Averages (Baseline context) - Updated: rolling_mean_by
                pl.col("observed_flux").rolling_mean_by("date", window_size="81d").alias("flux_81d_avg"),
                pl.col("observed_flux").rolling_mean_by("date", window_size="7d").alias("flux_7d_avg"),
                # Lag Features (Thermal Inertia - Takes days to heat atmosphere)
                pl.col("observed_flux").shift(1).alias("flux_lag_1d"),
                pl.col("observed_flux").shift(2).alias("flux_lag_2d"),
                pl.col("observed_flux").shift(3).alias("flux_lag_3d"),
            ])

        # 2. KP/AP (3-Hourly): Fast-acting magnetic storms
        if not kp_df.is_empty():
            kp_df = kp_df.sort("date").with_columns([
                # Lags (Magnetic storms hit the atmosphere in 3-6 hours)
                pl.col("ap_value").shift(1).alias("ap_lag_3h"),
                pl.col("ap_value").shift(2).alias("ap_lag_6h"),
                # Rolling Means (24h = 8 periods of 3h) - Updated: rolling_mean_by
                pl.col("ap_value").rolling_mean_by("date", window_size="24h").alias("ap_24h_mean"),
                pl.col("kp_value").rolling_mean_by("date", window_size="24h").alias("kp_24h_mean"),
            ])

        # 3. SUNSPOT (Daily): Macro climate
        if not sunspot_df.is_empty():
            sunspot_df = sunspot_df.sort("date").with_columns([
                # Updated: rolling_mean_by
                pl.col("sunspot_number").rolling_mean_by("date", window_size="30d").alias("sunspot_30d_avg"),
                pl.col("sunspot_number").rolling_mean_by("date", window_size="81d").alias("sunspot_81d_avg"),
            ])

        # 4. MERGE: Unified Global Density Timeline
        # Use the highest frequency dataframe (Kp - 3 hourly) as the backbone.
        # This ensures we don't lose any high-frequency data during the merge.
        unified = kp_df

        # ASOF Join (Backward) guarantees we never look into the future
        # This prevents data leakage - our models won't cheat by seeing tomorrow's data.
        if not flux_df.is_empty():
            unified = unified.join_asof(flux_df, on="date", strategy="backward")
        if not sunspot_df.is_empty():
            unified = unified.join_asof(sunspot_df, on="date", strategy="backward")

        # Physics-derived Activity Indicators
        # These ratios help our models understand relative changes vs absolute values.
        unified = unified.with_columns([
            # Flux Enhancement (Ratio of today's flux vs 81-day baseline)
            pl.when(pl.col("flux_81d_avg") > 0)
            .then(pl.col("observed_flux") / pl.col("flux_81d_avg"))
            .otherwise(None).alias("flux_enhancement"),

            # Day of year calculation for solar elevation proxy
            pl.col("date").dt.ordinal_day().alias("day_of_year")
        ]).with_columns([
            # Boolean/Integer Flags for Model Attention
            (pl.col("flux_enhancement") > 1.2).cast(pl.Int32).alias("solar_active"),
            (pl.col("flux_enhancement") > 1.5).cast(pl.Int32).alias("solar_very_active"),
            (pl.col("kp_value") <= 2.0).cast(pl.Int32).alias("geomag_quiet"),
            (pl.col("kp_value") >= 5.0).cast(pl.Int32).alias("geomag_storm"),
            (pl.col("kp_value") >= 7.0).cast(pl.Int32).alias("geomag_severe_storm"),
        ]).with_columns([
            ((pl.col("geomag_storm") == 1) | (pl.col("solar_active") == 1)).cast(pl.Int32).alias("high_activity_period")
        ])

        # Forward fill to cover any minor NaNs resulting from Asof joins (Safe filling)
        unified = unified.fill_null(strategy="forward")

        return unified