from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.shared.utils.hashing_service import HashingService
from src.shared.config.config_interfaces import PipelineConfigInterface


@dataclass
class ExecutionRequest:
    """
    Represents a pipeline execution request with hashed parameters for deduplication.

    Field Usage by Phase:
    - satellite_ids: Phase 1, 2, 6, 7 (orbital data phases)
    - input_data_type: All phases (required)
    - source: All phases (required)
    - processing_stage: All phases (required)
    - config_hash: Phase 1 only (API config tracking)
    - credentials_hash: Phase 1 only (API auth tracking)
    - active_ids: Phase 1 only (space-track specific)
    - manifest: Phase 2, 4, 5, 6, 7, 8 (input files from previous phase)
    - is_incremental: Phase 1, 2 (incremental collection/processing)
    """

    # Core fields (required for all phases)
    input_data_type: str
    source: str
    processing_stage: str

    # Phase-specific fields
    satellite_ids: Optional[List[str]] = field(default_factory=list)  # Phase 1,2,6,7
    manifest: Optional[List[str]] = None  # Phase 2,4,5,6,7,8
    is_incremental: bool = False  # Phase 1,2

    # Phase 1 only (space-track API tracking)
    config_hash: Optional[str] = None  # Phase 1 only
    credentials_hash: Optional[str] = None  # Phase 1 only
    active_ids: Optional[List[str]] = None  # Phase 1 only

    # Computed fields (auto-generated)
    parameters: Dict[str, Any] = field(init=False, repr=False)
    hash: str = field(init=False)
    created_at: datetime = field(default_factory=datetime.now, compare=False)

    def __post_init__(self) -> None:
        """Computes hash and parameters after dataclass initialization."""
        # Normalize satellite_ids
        self.satellite_ids = sorted(self.satellite_ids) if self.satellite_ids else []

        # Normalize active_ids (Phase 1 only)
        if self.active_ids:
            self.active_ids = sorted(self.active_ids)

        # Build parameters and compute hash
        self.parameters = self._build_parameters()
        self.hash = HashingService.for_parameters(self.parameters)

    def _build_parameters(self) -> Dict[str, Any]:
        """
        Builds parameter dictionary for hash generation.
        Only includes fields that affect execution uniqueness.
        """
        # Core parameters (always included)
        params = {
            'satellite_ids': self.satellite_ids,
            'input_data_type': self.input_data_type,
            'source': self.source,
            'processing_stage': self.processing_stage
        }

        # Phase 1 specific (API tracking)
        if self.config_hash:
            params['config_hash'] = self.config_hash
        if self.credentials_hash:
            params['credentials_hash'] = self.credentials_hash
        if self.active_ids:
            params['active_ids'] = self.active_ids

        # Input manifest (affects hash for downstream phases)
        if self.manifest:
            params['manifest'] = self.manifest

        # Incremental flag (affects collection strategy)
        if self.is_incremental:
            params['is_incremental'] = self.is_incremental

        return params

    @classmethod
    def from_config(cls,
                    pipeline_config: PipelineConfigInterface,
                    input_data_type: str,
                    source: str,
                    processing_stage: str,
                    satellite_ids: Optional[List[str]] = None,
                    **kwargs) -> 'ExecutionRequest':
        """
        Factory method to create ExecutionRequest from pipeline configuration.

        Args:
            pipeline_config: Pipeline configuration interface
            input_data_type: Type of data being processed (required)
            source: Data source identifier (required)
            processing_stage: Phase name (required)
            satellite_ids: List of satellite IDs (optional, for orbital phases)
            **kwargs: Additional optional parameters:
                - manifest: List of input files
                - is_incremental: Boolean flag for incremental mode
                - active_ids: List of active satellite IDs (Phase 1 only)

        Returns:
            ExecutionRequest instance with auto-generated hashes
        """
        # Generate system hashes only for Phase 1 (space-track)
        system_hashes = {}
        if source == "space-track" and processing_stage == "orbital_collection":
            system_hashes = cls._create_config_hashes(pipeline_config)

        return cls(
            satellite_ids=satellite_ids or [],
            input_data_type=input_data_type,
            source=source,
            processing_stage=processing_stage,
            manifest=kwargs.get("manifest"),
            is_incremental=kwargs.get("is_incremental", False),
            config_hash=system_hashes.get('config_hash'),
            credentials_hash=system_hashes.get('credentials_hash'),
            active_ids=kwargs.get('active_ids'))

    @staticmethod
    def _create_config_hashes(pipeline_config: PipelineConfigInterface) -> Dict[str, str]:
        api_endpoint = str(pipeline_config.get_space_track_base_url())

        identity = {'api': api_endpoint, 'input_data_type': 'orbital_elements'}
        config_hash = HashingService.for_parameters(identity)[:12]

        username = pipeline_config.get_space_track_username()
        credentials_hash = f'usr_{username[:6]}' if username else 'anon'

        return {
            'config_hash': config_hash,
            'credentials_hash': credentials_hash
        }


    def get_summary(self) -> Dict[str, Any]:
        """Returns human-readable execution request summary."""
        return {
            'satellite_count': len(self.satellite_ids),
            'input_data_type': self.input_data_type,
            'source': self.source,
            'processing_stage': self.processing_stage,
            'config_hash': self.config_hash,
            'credentials_hash': self.credentials_hash,
            'request_hash': self.hash[:16] + '...'
        }

    def __repr__(self) -> str:
        return (f'ExecutionRequest('
                f'hash={self.hash[:8]}..., '
                f'satellites={len(self.satellite_ids)}, '
                f'type={self.input_data_type}, '
                f'source={self.source}, '
                f'stage={self.processing_stage})')