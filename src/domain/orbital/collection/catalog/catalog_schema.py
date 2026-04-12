from __future__ import annotations
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# Storage / Persistence Contract
SatelliteCategory = Literal['calibration', 'target', 'selected_target', 'selected_calibration']

class SatelliteCatalog(BaseModel):
    """Schema for satellite lists stored in S3."""
    model_config = ConfigDict(frozen=True)

    category: SatelliteCategory
    satellite_ids: List[str]
    satellite_metadata: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    seed: Optional[int] = None

    @property
    def count(self) -> int:
        """Dynamically computes the count from the list of IDs."""
        return len(self.satellite_ids)

