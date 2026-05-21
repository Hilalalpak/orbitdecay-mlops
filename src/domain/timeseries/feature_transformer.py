import polars as pl


class TimeSeriesTransformer:
    def __init__(self, logger) -> None:
        self.logger = logger

    def merge_and_enrich(self, sat_id_str: str, orbital_df: pl.DataFrame, environment_df: pl.DataFrame) -> pl.DataFrame:
        if orbital_df.is_empty() or environment_df.is_empty():
            return pl.DataFrame()

        merged = orbital_df.sort("epoch_dt").join_asof(
            environment_df.sort("date"),
            left_on="epoch_dt",
            right_on="date",
            strategy="backward")

        merged = merged.with_columns([
            pl.lit(sat_id_str).alias("norad_cat_id"),
            pl.col("epoch_dt").alias("epoch"),
            pl.col("altitude_km").alias("altitude"),

            # Rename raw kp/ap columns to match DB schema
            pl.col("kp_value").alias("kp_mean"),
            pl.col("ap_value").alias("ap_mean"),
            pl.col("rul_days").alias("days_until_decay"),

            # Risk Score
            pl.when(pl.col("altitude_km") < 400)
            .then((400 - pl.col("altitude_km")) / 100)
            .otherwise(0.0).alias("low_altitude_risk"),

            (
                    pl.col("altitude_km").diff() /
                    (pl.col("epoch_dt").diff().dt.total_seconds() / 86400.0)
            ).alias("altitude_change_rate")
        ])

        target_cols = ["epoch", "date", "norad_cat_id", "mean_motion", "eccentricity",
            "inclination", "ra_of_asc_node", "arg_of_pericenter", "mean_anomaly", "bstar",
            "mean_motion_dot", "semimajor_axis", "altitude", "observed_flux", "flux_81d_avg",
            "flux_7d_avg", "kp_mean", "ap_mean", "altitude_change_rate", "ap_lag_3h", "ap_lag_6h", "ap_24h_mean",
            "kp_24h_mean", "sunspot_number", "flux_enhancement", "solar_active",
            "geomag_storm", "high_activity_period", "thermometer_density_index",
            "thermometer_sat_count", "thermometer_density_3d_avg", "low_altitude_risk", "days_until_decay"
        ]

        return merged.select([c for c in target_cols if c in merged.columns])