import polars as pl


class TargetLabelGenerator:
    """
    Generates training target labels (RUL).
    Not used during inference.
    """

    def apply(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.with_columns([
            self._rul_days()
        ])

        df = df.with_columns([
            self._log_rul()
        ])

        return df

    def _rul_days(self) -> pl.Expr:
        return (
            pl.when(pl.col("decay_date").is_not_null())
            .then(
                (pl.col("decay_date").str.strptime(pl.Datetime) - pl.col("epoch_dt"))
                .dt.total_days())
            .otherwise(None)
            .alias("rul_days"))

    def _log_rul(self) -> pl.Expr:
        return (
            pl.when(pl.col("rul_days").is_not_null() & (pl.col("rul_days") >= 0))
            .then((pl.col("rul_days") + 1).log())
            .otherwise(None)
            .alias("log_rul"))
