"""
Resolves how satellites should be grouped before processing. This keeps grouping
rules centralized and easy to adjust.
"""

from typing import Dict, List, Union
from structlog.stdlib import BoundLogger

class GroupResolver:

    def __init__(self, logger: BoundLogger) -> None:
        self.logger = logger

    def group_by_sat(self, data_list: Union[List[Dict], Dict]) -> Dict[str, List[Dict]]:
        """Groups data by satellite ID. Handles both list and dict inputs."""
        grouped: Dict[str, List[Dict]] = {}

        if not isinstance(data_list, list):
            self.logger.warning(f"Data for grouping was not a list (Type: {type(data_list)}). Skipping group.")
            return grouped

        for record in data_list:
            sat_id = record.get('NORAD_CAT_ID') or record.get('norad_cat_id')
            if sat_id:
                key = str(sat_id)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

        total = sum(len(v) for v in grouped.values())
        self.logger.debug(f"Grouped {total} records for {len(grouped)} satellites.")

        return grouped