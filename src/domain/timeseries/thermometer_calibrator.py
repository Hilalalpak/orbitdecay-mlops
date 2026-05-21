import polars as pl
from structlog.stdlib import BoundLogger

from src.shared.config.config_interfaces import DomainConfigInterface


class ThermometerCalibrator:

    def __init__(self, domain_config: DomainConfigInterface, logger: BoundLogger) -> None:
        self.logger = logger
        self.earth_radius_km = domain_config.get_earth_equatorial_radius_km()

        self.MAX_ECCENTRICITY = 0.05
        self.MIN_BSTAR = 1e-6
        self.MAX_MANEUVER_JUMP = 0.01
        self.ALT_BIN_SIZE = 100  # 100 km altitude bins

    def generate_empirical_density(self, active_sats_df: pl.DataFrame) -> pl.DataFrame:

        self.logger.debug("Starting thermometer calibration (Altitude-aware)...")

        # 1. Physical filtering
        df = active_sats_df.filter(
            (pl.col("eccentricity") < self.MAX_ECCENTRICITY) &
            (pl.col("bstar").abs() > self.MIN_BSTAR) &
            (pl.col("mean_motion_dot").is_not_null()) &
            (pl.col("semimajor_axis").is_not_null()))

        # 2. Maneuver filter
        df = df.sort(["norad_cat_id", "epoch"])
        df = df.with_columns(
            pl.col("mean_motion").diff().over("norad_cat_id").abs().alias("mm_jump")
        ).filter(
            pl.col("mm_jump") < self.MAX_MANEUVER_JUMP)

        # 3. Calculate altitude (km)
        df = df.with_columns(
            (pl.col("semimajor_axis") - self.earth_radius_km).alias("altitude_km"))

        # 4. Altitude bin (100 km intervals)
        df = df.with_columns(
            (
                (pl.col("altitude_km") // self.ALT_BIN_SIZE)
                * self.ALT_BIN_SIZE
            ).alias("alt_bin"))

        # 5. Altitude-normalized drag proxy
        df = df.with_columns(
            (
                (pl.col("mean_motion_dot") / pl.col("bstar")) /
                (pl.col("semimajor_axis") ** 2))
            .abs()
            .alias("empirical_drag_proxy"))

        # 6. Daily date
        df = df.with_columns(
            pl.col("epoch_dt").dt.truncate("1d").alias("date"))

        # 7. Daily density (by alt_bin)
        daily_bin_density = (
            df.group_by(["date", "alt_bin"])
              .agg([
                  pl.col("empirical_drag_proxy").median().alias("bin_density"),
                  pl.col("norad_cat_id").n_unique().alias("bin_sat_count")
              ])
              .sort(["date", "alt_bin"]))

        # 8. Global density (median of bin medians)
        daily_global_density = (
            daily_bin_density.group_by("date")
            .agg([
                pl.col("bin_density").median().alias("thermometer_density_index"),
                pl.col("bin_sat_count").sum().alias("thermometer_sat_count")
            ])
            .sort("date"))

        # 9. 3-day smoothing
        daily_global_density = daily_global_density.with_columns([
            pl.col("thermometer_density_index")
              .rolling_mean_by("date", window_size="3d")
              .alias("thermometer_density_3d_avg")
        ]).fill_null(strategy="forward")

        self.logger.info(
            f"Calibration completed. Generated {daily_global_density.height} daily global indices.")

        return daily_global_density