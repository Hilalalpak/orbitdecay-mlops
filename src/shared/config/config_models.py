"""
Pydantic configuration models used across the pipeline.
These models provide structured config access while maintaining backward
compatibility for legacy `.get()` and `config['key']` based lookups.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union, Optional


class LegacyConfigMixin:

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            return getattr(self, key)

        model_fields = getattr(self, "model_fields", {})
        for field_name, field_info in model_fields.items():
            if getattr(field_info, "alias", None) == key:
                return getattr(self, field_name)

        return default

    def __getitem__(self, item):
        value = self.get(item)
        if value is None:
            raise KeyError(f"Key '{item}' not found in config.")
        return value

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
            return

        model_fields = getattr(self, "model_fields", {})
        for field_name, field_info in model_fields.items():
            if getattr(field_info, "alias", None) == key:
                setattr(self, field_name, value)
                return

        setattr(self, key, value)


# Storage Config

class StorageConfigModel(BaseModel):
    s3_endpoint_url: str = Field(..., alias="storage__s3__endpoint_url")
    s3_access_key: str = Field(..., alias="storage__s3__access_key")
    s3_secret_key: str = Field(..., alias="storage__s3__secret_key")

    def get_s3_endpoint(self) -> str: return self.s3_endpoint_url
    def get_s3_access_key(self) -> str: return self.s3_access_key
    def get_s3_secret_key(self) -> str: return self.s3_secret_key


# Domain Config

class DomainConfigModel(BaseModel):
    earth_gravitational_parameter: float = Field(..., alias="physical_constants__earth__gravitational_parameter")
    earth_equatorial_radius_km: float = Field(6378.0, alias="physical_constants__earth__equatorial_radius_km")
    risk_thresholds: Dict[str, float] = Field(..., alias="orbital__risk_thresholds")

    def get_earth_equatorial_radius_km(self) -> float: return self.earth_equatorial_radius_km
    def get_earth_gravitational_parameter(self) -> float: return self.earth_gravitational_parameter
    def get_risk_thresholds(self) -> Dict[str, float]: return self.risk_thresholds


# Catalog Config

class CatalogConfigModel(BaseModel, LegacyConfigMixin):
    dynamic_seed: int = Field(..., alias="satellite_selection__random_seed")
    dynamic_categories: Dict[str, Any] = Field(..., alias="satellite_selection__categories")
    calibration_count: int = Field(..., alias="satellite_selection__categories__calibration__count")
    calibration_query: str = Field(..., alias="satellite_selection__categories__calibration__query")
    target_count: int = Field(..., alias="satellite_selection__categories__target__count")
    target_query: str = Field(..., alias="satellite_selection__categories__target__query")
    min_orbit_days: int = Field(60, alias="satellite_catalog__min_orbit_days")
    anchor_calibration_ids: List[str] = Field(default_factory=list, alias="satellite_selection__categories__calibration__anchor_calibration_ids")
    solar_cycle_regimes: Dict[str, List[List[int]]] = Field(default_factory=dict, alias="satellite_selection__solar_cycle_regimes")
    calibration_period_bands: Dict[str, int] = Field(default_factory=dict, alias="satellite_selection__calibration_period_bands")

    def get_dynamic_selection_seed(self) -> int: return self.dynamic_seed
    def get_calibration_count(self) -> int: return self.calibration_count
    def get_calibration_query(self) -> str: return self.calibration_query
    def get_target_count(self) -> int: return self.target_count
    def get_target_query(self) -> str: return self.target_query
    def get_min_orbit_days(self) -> int: return self.min_orbit_days
    def get_anchor_calibration_ids(self) -> List[str]: return self.anchor_calibration_ids
    def get_solar_cycle_regimes(self) -> Dict[str, List[List[int]]]: return self.solar_cycle_regimes
    def get_calibration_period_bands(self) -> Dict[str, int]: return self.calibration_period_bands


# Processing Config

class ProcessingConfigModel(BaseModel):
    max_workers: int = Field(..., alias="processing__parallel__max_workers")
    batch_limits: Dict[str, Any] = Field(..., alias="processing__batch_limits")
    numeric_fields: List[str] = Field(..., alias="processing__omm__numeric_fields")
    critical_columns: List[str] = Field(default_factory=list, alias="processing__omm__critical_columns")
    angular_columns: List[str] = Field(default_factory=list, alias="processing__omm__angular_columns")
    sentinel_values: List[str] = Field(default_factory=list, alias="processing__omm__sentinel_values")
    static_columns_to_keep: Dict[str, List[str]] = Field(default_factory=dict, alias="processing__orbital_propagation__static_columns_to_keep")
    filter_tba: bool = Field(..., alias="processing__omm__filter_tba_objects")
    date_range: Dict[str, str] = Field(..., alias="processing__date_range")
    quality_checks: bool = Field(..., alias="processing__validation__enable_quality_checks")
    min_data_points: int = Field(..., alias="processing__validation__min_data_points")
    max_gap_days: int = Field(..., alias="processing__validation__max_gap_days")
    enable_orbit_classification: bool = Field(..., alias="processing__omm__enable_orbit_classification")
    enable_position_calculation: bool = Field(..., alias="processing__omm__enable_position_calculation")
    orbital_cleaning: Dict[str, Dict[str, Any]] = Field(..., alias="processing__orbital_cleaning")
    orbital_segmentation: Dict[str, Dict[str, float]] = Field(..., alias="processing__orbital_segmentation")
    segment_filter: Dict[str, Dict[str, Any]] = Field(..., alias="processing__segment_filter")
    orbital_propagation: Dict[str, Dict[str, Any]] = Field(..., alias="processing__orbital_propagation")
    far_from_tle_minutes: int = Field(720, alias="processing__feature_engineering__far_from_tle_minutes")

    def get_orbital_propagation_config(self) -> Dict[str, Dict[str, Any]]: return self.orbital_propagation
    def get_far_from_tle_minutes(self) -> int: return self.far_from_tle_minutes
    def get_segment_filter_config(self) -> Dict[str, Dict[str, Any]]: return self.segment_filter
    def get_orbital_segmentation_config(self) -> Dict[str, Dict[str, float]]: return self.orbital_segmentation
    def get_orbital_cleaning_config(self) -> Dict[str, Dict[str, Any]]: return self.orbital_cleaning
    def get_max_workers(self) -> int: return self.max_workers
    def get_batch_limits(self) -> Dict[str, Any]: return self.batch_limits
    def get_numeric_omm_fields(self) -> List[str]: return self.numeric_fields
    def get_critical_columns(self) -> List[str]: return self.critical_columns
    def get_angular_columns(self) -> List[str]: return self.angular_columns
    def get_sentinel_values(self) -> List[str]: return self.sentinel_values
    def get_static_columns_to_keep(self) -> List[str]:
        """Extract static columns from the common section of orbital propagation config."""
        return self.static_columns_to_keep.get("common", [])
    def filter_tba_objects(self) -> bool: return self.filter_tba
    def get_date_range(self) -> Dict[str, str]: return self.date_range
    def is_quality_check_enabled(self) -> bool: return self.quality_checks
    def get_min_data_points(self) -> int: return self.min_data_points
    def get_max_gap_days(self) -> int: return self.max_gap_days
    def is_orbit_classification_enabled(self) -> bool: return self.enable_orbit_classification
    def is_position_calculation_enabled(self) -> bool: return self.enable_position_calculation


# Scheduling Config

class SchedulingConfigModel(BaseModel):
    model_training_enabled: bool = Field(..., alias="scheduling__model_training__enabled")
    daily_reports_schedule: str = Field(..., alias="scheduling__daily_reports__schedule")

    def is_model_training_enabled(self) -> bool: return self.model_training_enabled
    def get_daily_reports_schedule(self) -> str: return self.daily_reports_schedule


# Logging Config

class LoggingConfigModel(BaseModel):
    level: str = Field(..., alias="logging__level")
    files: Dict[str, str] = Field(..., alias="logging__files")
    environment_name: str = Field(..., alias="environment__name")

    def get_log_level(self) -> str: return self.level
    def get_log_files(self) -> Dict[str, str]: return self.files
    def get_environment_name(self) -> str: return self.environment_name


# Machine Learning Config

class MLConfigModel(BaseModel):
    tracking_uri: str = Field(..., alias="mlflow__tracking_uri")
    registry_name: str = Field(..., alias="mlflow__model_registry__default_model_name")
    orbital_features_enabled: bool = Field(True, alias="machine_learning__features__enable_orbital_features")
    experiment_name: str = Field(..., alias="mlflow__experiment_name")
    lstm_params: Dict[str, Any] = Field(..., alias="machine_learning__lstm")
    production_run_id: str = Field("", alias="mlflow__model_registry__production_run_id")
    risk_score_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {"critical": 0.8, "high": 0.6, "medium": 0.4, "low": 0.0},
        alias="machine_learning__risk_score_thresholds")

    def get_mlflow_tracking_uri(self) -> str: return self.tracking_uri
    def get_default_model_registry_name(self) -> str: return self.registry_name
    def is_orbital_features_enabled(self) -> bool: return self.orbital_features_enabled
    def get_mlflow_experiment_name(self) -> str: return self.experiment_name
    def get_lstm_params(self) -> Dict[str, Any]: return self.lstm_params
    def get_mlflow_production_run_id(self) -> str: return self.production_run_id
    def get_risk_score_thresholds(self) -> Dict[str, float]: return self.risk_score_thresholds


# Monitoring Config

class MonitoringConfigModel(BaseModel):
    prometheus_enabled: bool = Field(..., alias="monitoring__metrics__enable_prometheus")
    failed_rate: float = Field(..., alias="monitoring__alerts__failed_requests_rate")
    compliance_enabled: bool = Field(..., alias="monitoring__compliance__enable_usage_monitoring")
    daily_warning: float = Field(..., alias="monitoring__compliance__daily_usage_warning")
    hourly_warning: float = Field(..., alias="monitoring__compliance__hourly_usage_warning")
    burst_warning: float = Field(..., alias="monitoring__compliance__burst_warning")
    daily_critical: float = Field(..., alias="monitoring__compliance__daily_usage_critical")
    cache_hit_rate_threshold: float = Field(..., alias="monitoring__smart_collection__cache_hit_rate_threshold")
    cache_size_alert_mb: int = Field(..., alias="monitoring__smart_collection__cache_size_alert_mb")
    enable_cache_monitoring: bool = Field(..., alias="monitoring__smart_collection__enable_cache_monitoring")
    collection_time_threshold: int = Field(..., alias="monitoring__performance__collection_time_threshold")
    api_usage_tracking: bool = Field(..., alias="monitoring__api_usage_tracking")
    compliance_alerts: bool = Field(..., alias="monitoring__compliance_alerts")
    high_risk_satellites_alert: int = Field(..., alias="monitoring__alerts__high_risk_satellites")
    processing_time_threshold_alert: int = Field(..., alias="monitoring__alerts__processing_time_threshold")
    health_checks_enabled: bool = Field(..., alias="monitoring__health_checks__enabled")
    metrics_collection_interval: int = Field(..., alias="monitoring__metrics__collection_interval")

    def is_prometheus_enabled(self) -> bool: return self.prometheus_enabled
    def get_failed_request_alert_rate(self) -> float: return self.failed_rate
    def is_compliance_monitoring_enabled(self) -> bool: return self.compliance_enabled
    def get_compliance_daily_warning(self) -> float: return self.daily_warning
    def get_compliance_hourly_warning(self) -> float: return self.hourly_warning
    def get_compliance_burst_warning(self) -> float: return self.burst_warning
    def get_compliance_daily_critical(self) -> float: return self.daily_critical
    def get_cache_hit_rate_threshold(self) -> float: return self.cache_hit_rate_threshold
    def get_cache_size_alert_mb(self) -> int: return self.cache_size_alert_mb
    def is_cache_monitoring_enabled(self) -> bool: return self.enable_cache_monitoring
    def get_collection_time_threshold(self) -> int: return self.collection_time_threshold
    def is_api_usage_tracking_enabled(self) -> bool: return self.api_usage_tracking
    def is_compliance_alerts_enabled(self) -> bool: return self.compliance_alerts
    def get_high_risk_satellites_alert(self) -> int: return self.high_risk_satellites_alert
    def get_processing_time_threshold_alert(self) -> int: return self.processing_time_threshold_alert
    def is_health_checks_enabled(self) -> bool: return self.health_checks_enabled
    def get_metrics_collection_interval(self) -> int: return self.metrics_collection_interval


# Pipeline Config

class PipelineConfigModel(BaseModel, LegacyConfigMixin):
    s3_buckets: Dict[str, str] = Field(..., alias="paths__s3_buckets")
    s3_prefixes: Dict[str, str] = Field(..., alias="paths__s3_prefixes")
    username: str = Field(..., alias="data_sources__space_track__username")
    password: str = Field(..., alias="data_sources__space_track__password")
    daily_limit: int = Field(..., alias="data_sources__space_track__max_daily_requests")
    refresh_days: int = Field(..., alias="smart_collection__cache__force_refresh_days")
    flux_skip: int = Field(..., alias="api_defaults__data_sources__flux__header_lines_to_skip")
    incremental_enabled: bool = Field(..., alias="smart_collection__incremental_updates__enabled")
    incremental_max_days: int = Field(..., alias="smart_collection__incremental_updates__max_incremental_days")
    incremental_overlap_hours: int = Field(..., alias="smart_collection__incremental_updates__overlap_hours")
    incremental_buffer_size: int = Field(..., alias="smart_collection__incremental_updates__buffer_size")
    data_sources: Dict[str, Dict[str, Any]] = Field(..., alias="data_sources")
    duplicate_detection: bool = Field(..., alias="smart_collection__enable_duplicate_detection")
    cache_max_size_mb: int = Field(..., alias="smart_collection__cache__max_cache_size_mb")
    base_url: str = Field(..., alias="data_sources__space_track__base_url")
    hourly_limit: int = Field(..., alias="data_sources__space_track__hourly_limit")
    burst_limit: int = Field(..., alias="data_sources__space_track__burst_limit")
    api_delay: int = Field(..., alias="data_sources__space_track__api_delay")
    max_retries: int = Field(..., alias="data_sources__space_track__max_retries")
    batch_timeout_multiplier: float = Field(3.0, alias="data_sources__space_track__batch_timeout_multiplier")
    retry_backoff_factor: float = Field(0.5, alias="data_sources__space_track__retry_backoff_factor")
    session_timeout: int = Field(..., alias="data_sources__space_track__session_timeout")
    full_batch_size: int = Field(..., alias="data_sources__space_track__full_batch_size")
    inc_batch_size: int = Field(..., alias="data_sources__space_track__incremental_batch_size")
    use_test_server: bool = Field(..., alias="data_sources__space_track__use_test_server")
    endpoints: Dict[str, Union[str, List[str]]] = Field(..., alias="data_sources__space_track__endpoints")
    rate_limit_buffer: int = Field(..., alias="data_sources__space_track__rate_limit_buffer")
    solar_flux_url: str = Field(..., alias="data_sources__solar_flux__url")
    kp_indices_url: str = Field(..., alias="data_sources__kp_indices__url")
    sunspot_url: str = Field(..., alias="data_sources__sunspot__url")

    execution_mode: Optional[str] = Field(None)
    target_date: Optional[str] = Field(None)

    def get_s3_bucket(self, name: str) -> str: return self.s3_buckets.get(name, name)
    def get_s3_prefix(self, name: str) -> str: return self.s3_prefixes.get(name, name)
    def get_space_track_username(self) -> str: return self.username
    def get_space_track_password(self) -> str: return self.password
    def get_space_track_daily_limit(self) -> int: return self.daily_limit
    def get_smart_collection_force_refresh_days(self) -> int: return self.refresh_days
    def get_flux_header_skip_lines(self) -> int: return self.flux_skip
    def is_incremental_updates_enabled(self) -> bool: return self.incremental_enabled
    def get_incremental_max_days(self) -> int: return self.incremental_max_days
    def get_incremental_overlap_hours(self) -> int: return self.incremental_overlap_hours
    def get_incremental_buffer_size(self) -> int: return self.incremental_buffer_size
    def is_duplicate_detection_enabled(self) -> bool: return self.duplicate_detection
    def get_cache_max_size_mb(self) -> int: return self.cache_max_size_mb
    def get_space_track_base_url(self) -> str: return self.base_url
    def get_space_track_hourly_limit(self) -> int: return self.hourly_limit
    def get_space_track_burst_limit(self) -> int: return self.burst_limit
    def get_space_track_api_delay(self) -> int: return self.api_delay
    def get_space_track_max_retries(self) -> int: return self.max_retries
    def get_batch_timeout_multiplier(self) -> float: return self.batch_timeout_multiplier
    def get_retry_backoff_factor(self) -> float: return self.retry_backoff_factor
    def get_space_track_session_timeout(self) -> int: return self.session_timeout
    def get_full_batch_size(self) -> int: return self.full_batch_size
    def get_inc_batch_size(self) -> int: return self.inc_batch_size
    def use_space_track_test_server(self) -> bool: return self.use_test_server
    def get_space_track_endpoint(self, name: str) -> Union[str, List[str]]: return self.endpoints.get(name, f"DEFAULT_{name}")
    def get_rate_limit_buffer(self) -> int: return self.rate_limit_buffer
    def get_solar_flux_url(self) -> str: return self.solar_flux_url
    def get_kp_indices_url(self) -> str: return self.kp_indices_url
    def get_sunspot_url(self) -> str: return self.sunspot_url

    def get_env_sources(self) -> Dict[str, Dict[str, Any]]:
        return {
            key: value
            for key, value in self.data_sources.items()
            if isinstance(value, dict) and "url" in value
        }

    def get_env_source_url(self, source_id: str) -> str:
        if source_id not in self.data_sources:
            raise ValueError(f"Unknown environment source: {source_id}")

        source = self.data_sources[source_id]

        if "url" not in source:
            raise ValueError(f"Source '{source_id}' does not contain a URL")

        return source["url"]
