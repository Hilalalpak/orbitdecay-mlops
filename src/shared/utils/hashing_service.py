import hashlib
import json
from typing import Dict

class HashingService:
    """
    Provides deterministic hash generation for pipeline reproducibility.
    Singleton pattern ensures consistent hashing across all components.
    """

    _instance = None

    def __new__(cls):
        """Enforces singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def for_data_signature(data: Dict) -> str:
        """Creates compact hash representing data structure fingerprint."""
        signature_data = {source: len(data) if hasattr(data, '__len__') else str(data)[:100] for source, data in data.items()}
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()[:16]

    @staticmethod
    def for_parameters(params: Dict) -> str:
        """Generates SHA-256 hash from normalized request parameters."""
        normalized = {}

        for key, value in params.items():
            if value is not None:
                if hasattr(value, 'isoformat'):
                    normalized[key] = value.isoformat()
                elif isinstance(value, (list, tuple)):
                    normalized[key] = sorted([str(x) for x in value])
                else:
                    normalized[key] = str(value)

        param_string = json.dumps(normalized, sort_keys=True)

        return hashlib.sha256(param_string.encode()).hexdigest()

    @staticmethod
    def for_filters(filter_params: Dict, algorithm: str='sha256') -> str:
        """Creates hash for filter configurations with algorithm selection."""
        normalized_params = {}

        for key, value in filter_params.items():
            if value is not None:
                if hasattr(value, 'isoformat'):
                    normalized_params[key] = value.isoformat()
                else:
                    normalized_params[key] = str(value)

        params_str = json.dumps(normalized_params, sort_keys=True)

        if algorithm == 'md5':
            return hashlib.md5(params_str.encode()).hexdigest()
        else:
            return hashlib.sha256(params_str.encode()).hexdigest()