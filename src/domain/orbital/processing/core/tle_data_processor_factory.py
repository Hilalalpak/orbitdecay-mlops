from structlog.stdlib import BoundLogger
from src.shared.config.config_interfaces import ProcessingConfigInterface, DomainConfigInterface
from src.domain.orbital.processing.engines.record_validator import OrbitRecordValidator
from .tle_data_processor import OrbitProcessor

class OrbitProcessorFactory:
    """Factory for creating OrbitProcessor instances."""

    def __init__(self,
                 processing_config: ProcessingConfigInterface,
                 domain_config: DomainConfigInterface,
                 record_validator: OrbitRecordValidator,
                 environment_name: str,
                 logger: BoundLogger):
        self.processing_config = processing_config
        self.domain_config = domain_config
        self.record_validator = record_validator
        self.environment_name = environment_name
        self.logger = logger

    def create(self) -> OrbitProcessor:
        return OrbitProcessor(
            self.processing_config,
            self.domain_config,
            self.record_validator,
            self.environment_name,
            self.logger)