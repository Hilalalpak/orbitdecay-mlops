"""Grouping utilities for Phase 2 processing."""

from typing import Dict, Optional
import polars as pl
from structlog.stdlib import BoundLogger


def group_by_satellite(data: pl.DataFrame, logger: Optional[BoundLogger] = None) -> Dict[str, pl.DataFrame]:
    """
    Groups DataFrame by satellite ID (NORAD Catalog ID).
    Returns dict mapping satellite ID to DataFrame.
    """
    try:
        grouped_raw = data.partition_by("NORAD_CAT_ID", as_dict=True, maintain_order=False)

        grouped = {
            str(k[0] if isinstance(k, tuple) else k): v
            for k, v in grouped_raw.items()}

        if logger:
            logger.debug("grouping_complete", total=data.height, sats=len(grouped))

        return grouped

    except Exception as e:
        if logger:
            logger.error("grouping_failed", error=str(e))
        return {}