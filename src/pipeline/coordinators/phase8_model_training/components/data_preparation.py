from typing import List, Optional, Tuple

import pandas as pd

from src.machine_learning.data_loader import DataLoader
from src.machine_learning.feature_engineering.survival_feature_engineer import FeatureEngineer


class TrainingDataPreparer:

    def __init__(self,
                 data_loader: DataLoader,
                 feature_engineer: FeatureEngineer,
                 logger,
                 target_date: Optional[str] = None) -> None:
        self.data_loader = data_loader
        self.feature_engineer = feature_engineer
        self.logger = logger
        self.target_date = target_date

    def load_satellite_data(self) -> List[Tuple[str, pd.DataFrame]]:
        satellites = self.data_loader.get_training_satellites(min_records=200)
        if not satellites:
            return []

        satellite_data_list = []
        for sat_id in satellites:
            df = self.data_loader.load(sat_id, self.target_date)
            if not df.empty:
                satellite_data_list.append((sat_id, df))

        return satellite_data_list

    def prepare_features(self, satellite_data_list: List[Tuple[str, pd.DataFrame]]):
        all_survival_data = []
        for sat_id, df in satellite_data_list:
            survival_data = self.feature_engineer.prepare_survival_data(df, sat_id)
            if not survival_data.empty:
                all_survival_data.append(survival_data)

        combined_survival_data = pd.concat(all_survival_data, ignore_index=True)
        return self.feature_engineer.prepare_features(combined_survival_data)
