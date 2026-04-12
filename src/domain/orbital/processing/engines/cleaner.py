import polars as pl
from typing import Dict, Any
from src.shared.config.config_interfaces import ProcessingConfigInterface
from src.shared.enums.dataset_enums import DatasetRole


class OrbitalDataCleaner:
    """
    Cleans raw TLE data via schema enforcement, artifact removal, and numeric preparation.
    Filters TBA objects, enforces critical field requirements, and applies domain constraints.
    """

    def __init__(self, orbital_cleaning_config: Dict[str, Dict[str, Any]], processing_config: ProcessingConfigInterface):
        self.config = orbital_cleaning_config
        self.sentinels = processing_config.get_sentinel_values()
        self.critical_cols = processing_config.get_critical_columns()
        self.angular_cols = processing_config.get_angular_columns()
        self.numeric_cols = processing_config.get_numeric_omm_fields()

    def process(self, df: pl.DataFrame, dataset_role: DatasetRole) -> pl.DataFrame:
        """Executes cleaning pipeline: normalization, filtering, and constraint enforcement."""
        role_cfg = self.config[dataset_role.value]

        max_ecc = role_cfg["max_eccentricity"]
        bstar_lim = role_cfg["bstar_limit"]
        allow_neg_bstar = role_cfg.get("allow_negative_bstar", False)

        df = df.select([pl.col(c).alias(c.lower()) for c in df.columns])

        df = self._normalize_schema_types(df)

        df = df.with_columns(
            pl.col("decay_date")
            .max()
            .over("norad_cat_id")
            .alias("decay_date"))

        if "object_name" in df.columns:
            df = df.filter(~pl.col("object_name").str.contains("TBA"))

        existing_criticals = [c for c in self.critical_cols if c in df.columns]
        df = df.drop_nulls(subset=existing_criticals)

        df = df.filter(pl.col("eccentricity").is_not_null() &
                       (pl.col("eccentricity") <= max_ecc))

        if 'bstar' in df.columns:
            df = df.with_columns(pl.col("bstar").fill_null(0.0))

            bstar_cond = pl.col("bstar").abs() <= bstar_lim
            if not allow_neg_bstar:
                bstar_cond &= pl.col("bstar") >= 0

            df = df.filter(bstar_cond)

        df = df.unique(subset=["norad_cat_id", "epoch"], keep="last")

        return df

    def _normalize_schema_types(self, df: pl.DataFrame) -> pl.DataFrame:
        """Enforces canonical dtypes for raw TLE schema."""
        exprs = []

        if "norad_cat_id" in df.columns:
            exprs.append(pl.col("norad_cat_id").cast(pl.Int64))

        if "epoch" in df.columns:
            exprs.append(
                pl.col("epoch")
                .cast(pl.Utf8)
                .str.to_datetime(strict=False)
                .alias("epoch_dt"))

        if "decay_date" in df.columns:
            exprs.append(
                pl.col("decay_date")
                .cast(pl.Utf8)
                .str.to_datetime(strict=False)
                .alias("decay_date"))

        for c in self.numeric_cols:
            if c in df.columns:
                exprs.append(self._clean_numeric_col(c))

        if exprs:
            df = df.with_columns(exprs)

        return df

    def _clean_numeric_col(self, col_name: str) -> pl.Expr:
        """Cleans numeric string columns by removing sentinels and casting to Float64."""
        return (
            pl.when(
                pl.col(col_name).cast(pl.Utf8).str.strip_chars().is_in(self.sentinels) |
                pl.col(col_name).cast(pl.Utf8).str.strip_chars().is_null() |
                (pl.col(col_name).cast(pl.Utf8).str.strip_chars() == ""))
            .then(None)
            .otherwise(pl.col(col_name))
            .cast(pl.Float64, strict=False)
            .alias(col_name))
