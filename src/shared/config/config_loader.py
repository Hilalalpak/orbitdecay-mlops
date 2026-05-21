"""
Loads, merges, and validates configuration files for the pipeline.
Handles defaults, environment overrides, key-flattening, and env-var resolution
before producing validated Pydantic configuration models.
"""

import yaml
import os
import sys
import re
from typing import Type, Any, cast, TypeVar, Dict
from pydantic import ValidationError, BaseModel

from .config_interfaces import (
    StorageConfigInterface, DomainConfigInterface, CatalogConfigInterface,
    ProcessingConfigInterface, SchedulingConfigInterface, LoggingConfigInterface,
    MLConfigInterface, MonitoringConfigInterface, PipelineConfigInterface)

from .config_models import (
    StorageConfigModel, DomainConfigModel, CatalogConfigModel,
    ProcessingConfigModel, SchedulingConfigModel, LoggingConfigModel,
    MLConfigModel, MonitoringConfigModel, PipelineConfigModel)

T = TypeVar("T", bound=BaseModel)

def _deep_merge(dict1: dict, dict2: dict) -> dict:
    """Recursively merges two dictionaries, letting dict2 override dict1."""
    result = dict1.copy()
    for key, value in (dict2 or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        elif value is not None:
            result[key] = value
    return result


class ConfigLoader:
    def __init__(self, base_path: str = 'infrastructure/config') -> None:
        self.raw_config: Dict[str, Any] = {}
        default_paths = {
            'core_base': f'{base_path}/defaults/core/base.yml',
            'core_storage': f'{base_path}/defaults/core/storage.yml',
            'core_monitoring': f'{base_path}/defaults/core/monitoring.yml',
            'data_sources': f'{base_path}/defaults/data/sources.yml',
            'data_processing': f'{base_path}/defaults/data/processing.yml',
            'data_collection': f'{base_path}/defaults/data/collection.yml',
            'data_catalog': f'{base_path}/defaults/data/catalog.yml',
            'ml_models': f'{base_path}/defaults/ml/models.yml',
            'ml_mlflow': f'{base_path}/defaults/ml/mlflow.yml',
            'domain_physics': f'{base_path}/defaults/domain/physics.yml',
            'domain_orbital': f'{base_path}/defaults/domain/orbital.yml',
            'services_api': f'{base_path}/defaults/services/api.yml',
            'services_batch': f'{base_path}/defaults/services/batch.yml'}

        for name, path in default_paths.items():
            try:
                with open(path, 'r') as f:
                    cfg = yaml.safe_load(f)
                    if cfg:
                        self.raw_config = _deep_merge(self.raw_config, cfg)
                print(f"[ConfigLoader] Loaded default: {name} ({path})")
            except FileNotFoundError:
                raise FileNotFoundError(f"Missing default config: {path}")
            except yaml.YAMLError as ye:
                raise RuntimeError(f"YAML parsing failed at {path}: {ye}")

        env = os.getenv("ENVIRONMENT", "dev")
        env_path = f'{base_path}/environments/{env}.yml'

        try:
            with open(env_path, 'r') as f:
                env_cfg = yaml.safe_load(f)
                if env_cfg:
                    self.raw_config = _deep_merge(self.raw_config, env_cfg)
            print(f"[ConfigLoader] Loaded environment override: {env} ({env_path})")
        except FileNotFoundError:
            print(f"[ConfigLoader] Warning: Env config not found: {env_path}")
        except yaml.YAMLError as ye:
            raise RuntimeError(f"YAML error in env config ({env_path}): {ye}")

        self.flat_config = self._flatten_config(self.raw_config)
        print("[ConfigLoader] Config flattened + env overrides applied.")

    @staticmethod
    def _resolve_value(value: Any, key: str) -> Any:
        """Returns env-variable override if available, otherwise resolves inline ${VAR:-fallback} syntax."""
        override = os.getenv(key.upper())
        if override is not None:
            return override

        if not isinstance(value, str):
            return value

        match = re.match(r"^\$\{(.*?)(:-(.*?))?\}$", value)
        if match:
            var_name = match.group(1)
            fallback = match.group(3)
            env_val = os.getenv(var_name)
            return env_val if env_val is not None else fallback or None

        return value

    @staticmethod
    def _flatten_config(d: dict, parent: str = '', sep: str = '__') -> dict:
        """Creates a flat dictionary from a nested one while preserving full nested keys."""
        flat = {}
        for k, v in d.items():
            new_key = f"{parent}{sep}{k}" if parent else k
            if isinstance(v, dict):
                flat[new_key] = v
                flat.update(ConfigLoader._flatten_config(v, new_key, sep))
            else:
                flat[new_key] = ConfigLoader._resolve_value(v, new_key)
        return flat

    def _load_model(self, model_class: Type[T]) -> T:
        try:
            return model_class.model_validate(self.flat_config)
        except ValidationError as e:
            print(f"[ConfigLoader] Validation failed for {model_class.__name__}", file=sys.stderr)
            print(e, file=sys.stderr)
            raise RuntimeError(f"Config validation error in {model_class.__name__}")

    def get_storage_config(self) -> StorageConfigInterface:
        return cast(StorageConfigInterface, self._load_model(StorageConfigModel))

    def get_domain_config(self) -> DomainConfigInterface:
        return cast(DomainConfigInterface, self._load_model(DomainConfigModel))

    def get_catalog_config(self) -> CatalogConfigInterface:
        return cast(CatalogConfigInterface, self._load_model(CatalogConfigModel))

    def get_processing_config(self) -> ProcessingConfigInterface:
        return cast(ProcessingConfigInterface, self._load_model(ProcessingConfigModel))

    def get_scheduling_config(self) -> SchedulingConfigInterface:
        return cast(SchedulingConfigInterface, self._load_model(SchedulingConfigModel))

    def get_logging_config(self) -> LoggingConfigInterface:
        return cast(LoggingConfigInterface, self._load_model(LoggingConfigModel))

    def get_ml_config(self) -> MLConfigInterface:
        return cast(MLConfigInterface, self._load_model(MLConfigModel))

    def get_monitoring_config(self) -> MonitoringConfigInterface:
        return cast(MonitoringConfigInterface, self._load_model(MonitoringConfigModel))

    def get_pipeline_config(self) -> PipelineConfigInterface:
        return cast(PipelineConfigInterface, self._load_model(PipelineConfigModel))