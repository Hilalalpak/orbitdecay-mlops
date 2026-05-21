import polars as pl
import numpy as np


class SpatioTemporalFeatureGenerator:
    """Computes time-solar-orbital interaction features."""

    def apply(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.with_columns(self._local_solar_time())
        df = df.with_columns(self._cos_lst())
        return df

    def _local_solar_time(self) -> pl.Expr:
        return (
            (
                (pl.col("epoch_dt").dt.hour() +
                 pl.col("epoch_dt").dt.minute() / 60.0)
                +
                (pl.col("ra_of_asc_node") / 15.0))
            .mod(24)
            .alias("local_solar_time"))

    def _cos_lst(self) -> pl.Expr:
        return (
            pl.when(pl.col("local_solar_time").is_not_null())
            .then(
                (2 * np.pi * pl.col("local_solar_time") / 24).cos())
            .otherwise(None)
            .alias("cos_lst"))
