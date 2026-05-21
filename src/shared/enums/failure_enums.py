from enum import Enum


class Phase1FailureReason(str, Enum):
    """Known failure reasons for Phase 1 orbital data collection."""
    NO_SATELLITES = "no_satellites_available"
    NO_DATA_RETRIEVED = "no_data_retrieved"
    MANIFEST_CREATION_FAILED = "manifest_creation_failed"
    API_QUOTA_EXCEEDED = "api_quota_exceeded"
    STRATEGY_EXECUTION_FAILED = "strategy_execution_failed"
    CACHE_ERROR = "cache_error"
    UNKNOWN_ERROR = "unknown_error"


class Phase2FailureReason(str, Enum):
    """Known failure reasons for Phase 2 orbital data processing."""
    NO_INPUT_DATA = "no_input_data"
    HASH_CREATION_FAILED = "hash_creation_failed"
    PROCESSING_FAILED = "processing_failed"
    UNKNOWN_ERROR = "unknown_error"


class Phase3FailureReason(str, Enum):
    """Known failure reasons for Phase 3 feature engineering."""
    NO_INPUT_DATA = "no_input_data"
    PROCESSING_FAILED = "processing_failed"
    CHECKPOINT_ERROR = "checkpoint_error"
    HASH_CREATION_FAILED = "hash_creation_failed"
    UNKNOWN_ERROR = "unknown_error"


class Phase4FailureReason(str, Enum):
    """Known failure reasons for Phase 4 environmental data collection."""
    NO_SOURCES = "no_sources"
    QUOTA_EXCEEDED = "quota_exceeded"
    DATA_VALIDATION_FAILED = "data_validation_failed"
    CACHE_WRITE_FAILED = "cache_write_failed"
    STRICT_MODE_FAILED = "strict_mode_failed"
    NO_DATA_RETRIEVED = "no_data_retrieved"
    UNKNOWN_ERROR = "unknown_error"


class Phase5FailureReason(str, Enum):
    """Known failure reasons for Phase 5 environmental data processing."""
    NO_INPUT_MANIFEST = "no_input_manifest"
    SOURCE_LOAD_FAILED = "source_load_failed"
    DATA_VALIDATION_FAILED = "data_validation_failed"
    PROCESSING_FAILED = "processing_failed"
    OUTPUT_SAVE_FAILED = "output_save_failed"
    UNKNOWN_ERROR = "unknown_error"
