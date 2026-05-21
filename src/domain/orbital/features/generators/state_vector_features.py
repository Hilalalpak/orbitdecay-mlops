import polars as pl
from structlog.stdlib import BoundLogger


class StateVectorFeatureGenerator:
    """
    Generates kinematic features from SGP4 state vectors.
    NULL-safe vector math, no row drops.
    """

    def __init__(self, logger: BoundLogger, earth_equatorial_radius_km: float, far_from_tle_minutes: int):
        self.logger = logger
        self.earth_radius_km = earth_equatorial_radius_km
        self.far_from_tle_minutes = far_from_tle_minutes

    def apply(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.with_columns([
            ((pl.col("vel_x") ** 2 + pl.col("vel_y") ** 2 + pl.col("vel_z") ** 2).sqrt()).alias("speed_km_s"),
            ((pl.col("pos_x") ** 2 + pl.col("pos_y") ** 2 + pl.col("pos_z") ** 2).sqrt()).alias("radius_km"),
            ((pl.col("pos_x") ** 2 + pl.col("pos_y") ** 2 + pl.col("pos_z") ** 2).sqrt() - self.earth_radius_km).alias(
                "altitude_km"),
            (
                    (pl.col("pos_x") * pl.col("vel_x") +
                     pl.col("pos_y") * pl.col("vel_y") +
                     pl.col("pos_z") * pl.col("vel_z"))
                    /
                    (pl.col("pos_x") ** 2 + pl.col("pos_y") ** 2 + pl.col("pos_z") ** 2).sqrt()
            ).alias("radial_velocity_km_s"),
        ])

        df = df.with_columns([
            (
                (pl.col("speed_km_s") ** 2 - pl.col("radial_velocity_km_s") ** 2)
                .clip(lower_bound=0)
                .sqrt()
            ).alias("tangential_velocity_km_s")
        ])

        df = df.with_columns([
            pl.when(
                pl.col("radial_velocity_km_s").is_not_null() &
                pl.col("tangential_velocity_km_s").is_not_null())
            .then(pl.arctan2(
                pl.col("radial_velocity_km_s"),
                pl.col("tangential_velocity_km_s")))
            .otherwise(None)
            .alias("flight_path_angle_rad"),

            pl.col("propagation_minutes").abs().alias("abs_propagation_minutes"),
            (pl.col("propagation_minutes").abs() > self.far_from_tle_minutes).alias("is_far_from_tle"),
        ])

        return df

