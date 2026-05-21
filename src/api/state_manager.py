import structlog
from typing import Any

# Core servisleri doğrudan import ediyoruz.
# Eğer bu servisler yoksa sistem hata verip durmalıdır (Fail-Fast).
from src.shared.config.config_loader import ConfigLoader
from src.machine_learning.satellite_risk_predictor import SatelliteSurvivalPredictor
from src.machine_learning.data_loader import DataLoader
from src.machine_learning.trainer_factory import TrainerFactory
from src.machine_learning.models.loader import ModelLoader
from src.machine_learning.feature_engineering.survival_feature_engineer import FeatureEngineer
from src.scheduler.daily_reporter import DailyReportScheduler
from src.monitoring import initialize_monitoring_instance

logger = structlog.get_logger(__name__)

# Global servis değişkenleri
config_loader: ConfigLoader
data_loader: DataLoader
predictor: SatelliteSurvivalPredictor
monitoring_system: Any = None
trainer_factory: TrainerFactory
daily_scheduler: DailyReportScheduler

SERVICE_STATUS = "inactive"
PREDICTOR_STATUS = "inactive"
MONITORING_STATUS = "inactive"

def init_services() -> None:
    """
    Core servisleri başlatır. Herhangi bir aşamada hata oluşursa
    sistem istisna fırlatır ve başlatmayı durdurur.
    """
    global config_loader, data_loader, predictor, trainer_factory, daily_scheduler
    global SERVICE_STATUS, PREDICTOR_STATUS

    logger.info("servisler_baslatiliyor")

    # 1. Konfigürasyon
    config_loader = ConfigLoader()
    ml_config = config_loader.get_ml_config()
    storage_config = config_loader.get_storage_config()
    scheduling_config = config_loader.get_scheduling_config()

    # 2. Temel Servisler (Hata durumunda exception fırlatır)
    # Note: DataLoader init requires only logger in its current implementation
    data_loader = DataLoader(logger=logger)
    trainer_factory = TrainerFactory(ml_config=ml_config)
    
    # Init predictor dependencies
    model_loader = ModelLoader(ml_config=ml_config, storage_config=storage_config)
    feature_engineer = FeatureEngineer(logger=logger)

    # 3. Ana Predicter
    predictor = SatelliteSurvivalPredictor(
        loader=data_loader,
        model_loader=model_loader,
        feature_engineer=feature_engineer,
        ml_config=ml_config
    )
    
    # Init scheduler
    daily_scheduler = DailyReportScheduler(
        predictor=predictor,
        data_loader=data_loader,
        scheduling_config=scheduling_config
    )

    PREDICTOR_STATUS = "active"
    SERVICE_STATUS = "active"

    logger.info("tüm_servisler_aktif")


def initialize_monitoring_system() -> None:
    """Monitoring sistemini başlatır."""
    global monitoring_system
    global MONITORING_STATUS

    # Konfigürasyon yoksa başlatma
    if not config_loader:
        raise RuntimeError("Monitoring başlatılamadı: ConfigLoader henüz yüklenmemiş.")

    monitoring_system = initialize_monitoring_instance(
        monitoring_config=config_loader.get_monitoring_config(),
        logging_config=config_loader.get_logging_config(),
        quota_manager=None
    )
    MONITORING_STATUS = "active"
    logger.info("prometheus_monitoring_sistemi_aktif")

def export_prometheus_metrics() -> bytes:
    """Exports prometheus metrics from the isolated custom registry."""
    if monitoring_system is not None:
        try:
            return monitoring_system.export_metrics()
        except Exception as e:
            logger.error("failed_to_export_metrics", error=str(e))
    return b""
