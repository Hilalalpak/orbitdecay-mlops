import polars as pl
from concurrent.futures import ThreadPoolExecutor, as_completed
from .timeseries_storage import TimeSeriesStorage
from .feature_transformer import TimeSeriesTransformer
from .thermometer_calibrator import ThermometerCalibrator


class TimeSeriesGenerator:
    def __init__(self, pipeline_config, domain_config, storage_adapter, logger) -> None:
        self.storage = TimeSeriesStorage(pipeline_config, storage_adapter, logger)
        self.transformer = TimeSeriesTransformer(logger)
        self.calibrator = ThermometerCalibrator(domain_config, logger)
        self.logger = logger

    def create_all_timeseries(self, max_workers: int = 8):
        environment_dataset = self.build_environment_dataset()

        decayed_paths = self.storage.list_decayed_latest_paths()
        if not decayed_paths:
            self.logger.warning("No DECAYED satellites found.")
            return {}

        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_single, p, environment_dataset): p
                       for p in decayed_paths}

            for f in as_completed(futures):
                results[futures[f]] = f.result()

        return results

    def _process_single(self, key: str, env_df: pl.DataFrame) -> bool:
        sat_id = key.split("/")[-3]

        self.logger.debug(f"[SAT-{sat_id}] Loading S3 data...")
        orb_df = self.storage.load_satellite_orbital_data(key)
        if orb_df.is_empty():
            return False

        max_epoch = self.storage.get_max_epoch(sat_id)
        if max_epoch is not None:
            before = orb_df.height
            orb_df = orb_df.filter(pl.col("epoch") > pl.lit(max_epoch))
            new_rows = orb_df.height
            if orb_df.is_empty():
                self.logger.debug(f"[SAT-{sat_id}] No new epochs, skipping.")
                return True
            self.logger.debug(f"[SAT-{sat_id}] Filtered {new_rows} new epochs from {before} rows.")

        self.logger.debug(f"[SAT-{sat_id}] Enriching with atmospheric data...")
        enriched = self.transformer.merge_and_enrich(sat_id, orb_df, env_df)

        self.logger.info(f"[SAT-{sat_id}] Writing to database ({enriched.height} rows)...")
        success = self.storage.save_satellite_timeseries(enriched)

        if success:
            self.logger.debug(f"[SAT-{sat_id}] SUCCESS.")

        return success

    def build_environment_dataset(self) -> pl.DataFrame:
        """
        1) Reads all ACTIVE latest orbital_history data
        2) Generates daily density using thermometer calibration
        3) Merges with space weather data
        4) Saves as Density_Dataset.parquet
        5) Returns the final environment dataset
        """

        self.logger.info("Phase-7 → Building Environment Dataset (ACTIVE + Weather)")

        # 1. Load ACTIVE latest
        active_paths = self.storage.list_active_latest_paths()

        if not active_paths:
            raise RuntimeError("No ACTIVE satellites found.")

        active_dfs = []
        for path in active_paths:
            df = self.storage.load_satellite_orbital_data(path)
            if not df.is_empty():
                active_dfs.append(df)

        if not active_dfs:
            raise RuntimeError("ACTIVE satellite data is empty.")

        active_all = pl.concat(active_dfs)

        self.logger.info(f"Loaded {len(active_dfs)} ACTIVE satellites.")

        # 2. Generate density
        density_index = self.calibrator.generate_empirical_density(active_all)

        # 3. Load Space Weather
        weather = self.storage.load_space_weather_data()

        # 4. Merge Weather + Density
        environment_dataset = (
            weather.join(density_index, on="date", how="left")
            .sort("date")
            .fill_null(strategy="forward"))

        self.logger.info(
            f"Environment dataset created with {environment_dataset.height} rows.")

        return environment_dataset