"""Business logic filters for satellite catalog selection."""
from typing import Dict, Any
from datetime import datetime, timezone
from src.domain.orbital.collection.catalog.catalog_schema import SatelliteCategory


def is_orbit_duration_valid(item: Dict[str, Any], category: SatelliteCategory, min_orbit_days: int) -> bool:
    """Validates that satellite orbited for minimum required duration."""
    launch_str = item['LAUNCH']

    try:

        launch = datetime.strptime(launch_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        if category == 'calibration':
            end_date = datetime.now(timezone.utc)
        else:
            decay_str = item['DECAY']

            end_date = datetime.strptime(decay_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        days = (end_date - launch).days
        return days >= min_orbit_days

    except ValueError:
        return False