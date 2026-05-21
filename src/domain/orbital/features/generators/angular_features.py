import polars as pl
import numpy as np


class CyclicOrbitalFeatureGenerator:
    """Converts angular orbital elements to sin/cos representations."""

    DEG2RAD = np.pi / 180.0

    def apply(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns([
        *self._sin_cos("ra_of_asc_node", "sin_raan", "cos_raan"),
        *self._sin_cos("arg_of_pericenter", "sin_arg_per", "cos_arg_per"),
        *self._sin_cos("mean_anomaly", "sin_mean_anomaly", "cos_mean_anomaly"),
    ])

    def _sin_cos(self, col: str, sin_name: str, cos_name: str) -> list[pl.Expr]:
        rad = pl.col(col) * self.DEG2RAD
        return [
            pl.when(pl.col(col).is_not_null())
              .then(rad.sin())
              .otherwise(None)
              .alias(sin_name),

            pl.when(pl.col(col).is_not_null())
              .then(rad.cos())
              .otherwise(None)
              .alias(cos_name)
        ]
