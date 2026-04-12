import polars as pl
from typing import Dict, Any
from src.shared.enums.dataset_enums import DatasetRole


class SegmentFilter:
    """
    Applies quality gates to orbital segments.
    Filters by duration and latency to ensure sufficient training history.
    """

    def __init__(self, segment_filter_config: Dict[str, Dict[str, Any]]):
        self.config = segment_filter_config

    def process(self, df: pl.DataFrame, dataset_role: DatasetRole) -> pl.DataFrame:
        """Filters segments by duration and latency thresholds."""
        role_cfg = self.config.get(dataset_role.value)

        if role_cfg is None:
            raise ValueError(f"No segment filter config for role: {dataset_role.value}")

        if role_cfg.get("skip_filtering", False):
            return df

        min_duration = role_cfg.get("min_duration_days", 30)
        max_latency = role_cfg.get("max_latency_hours", 48)

        df = df.with_columns(pl.col("decay_date").cast(pl.String))

        seg_stats = df.group_by("segment_id").agg([
            pl.col("epoch_dt").min().alias("seg_start"),
            pl.col("epoch_dt").max().alias("seg_end"),
            pl.col("decay_date").first().alias("true_decay_date")])

        if dataset_role.value == "decayed":
            last_segment = (
                seg_stats
                .sort("seg_end")
                .select("segment_id")
                .tail(1))

            if last_segment.is_empty():
                return pl.DataFrame()

            last_id = last_segment["segment_id"][0]

            df = df.filter(pl.col("segment_id") == last_id)

            seg_stats = seg_stats.filter(pl.col("segment_id") == last_id)

        seg_stats = seg_stats.with_columns([
            (pl.col("seg_end") - pl.col("seg_start"))
            .dt.total_days().alias("duration_days"),

            (pl.col("true_decay_date").str.to_datetime(strict=False) - pl.col("seg_end"))
            .dt.total_hours().fill_null(0).alias("latency_hours")])

        valid_segments = seg_stats.filter(
            (pl.col("duration_days") >= min_duration) &
            (pl.col("latency_hours") <= max_latency))

        valid_ids = valid_segments["segment_id"]
        return df.filter(pl.col("segment_id").is_in(valid_ids))