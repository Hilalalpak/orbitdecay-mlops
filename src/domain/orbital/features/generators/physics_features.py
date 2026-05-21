import polars as pl


class PhysicsDerivedGenerator:
    """
    Generates physics-derived features from orbital elements.
    NULL-safe, never drops rows.
    """

    def __init__(self, earth_equatorial_radius_km: float):
        self.earth_radius_km = earth_equatorial_radius_km

    def apply(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns([
            self._log_bstar(),
            self._perigee_altitude(),
            self._mean_motion_derivative()
        ])

    def _log_bstar(self) -> pl.Expr:
        return (
            pl.when(pl.col("bstar").is_not_null() & (pl.col("bstar") != 0))
            .then(pl.col("bstar").abs().log10())
            .otherwise(None)
            .alias("log_bstar"))

    def _perigee_altitude(self) -> pl.Expr:
        return (
            pl.when(
                pl.col("semimajor_axis").is_not_null() &
                pl.col("eccentricity").is_not_null())
            .then(
                pl.col("semimajor_axis") * (1 - pl.col("eccentricity")) - self.earth_radius_km)
            .otherwise(None)
            .alias("perigee_alt_km"))

    def _mean_motion_derivative(self) -> pl.Expr:
        return (
            (
                pl.col("mean_motion") -
                pl.col("mean_motion").shift(1)
            ) /
            (
                (pl.col("epoch_dt") - pl.col("epoch_dt").shift(1))
                .dt.total_days()
            )
        ).over("segment_id").alias("calc_mean_motion_dot")