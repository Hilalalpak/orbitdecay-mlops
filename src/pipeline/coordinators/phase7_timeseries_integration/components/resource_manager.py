from src.shared.config.config_models import ProcessingConfigModel

class TimeseriesResourceManager:
    def __init__(self, processing_config: ProcessingConfigModel, execution_mode: str) -> None:
        self.processing_config = processing_config
        self.execution_mode = execution_mode

    def calculate_workers(self) -> int:
        """Calculates optimized worker count based on execution mode."""
        base_workers = self.processing_config.get_max_workers()

        if self.execution_mode == 'prod':
            # Prod optimization logic from original code
            return min(base_workers * 2, 16)
        elif self.execution_mode == 'test':
            # Test optimization logic from original code
            return max(4, base_workers)
        else:
            # Default/Dev optimization logic from original code
            return max(2, base_workers // 2)