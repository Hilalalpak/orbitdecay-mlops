
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class EnrichedOrbitRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    # --- 1. Identity & Metadata ---
    norad_cat_id: int = Field(...)
    segment_id: str = Field(...)

    object_type: Optional[str] = Field(None)
    launch_date: Optional[str] = Field(None)
    creation_date: Optional[str] = Field(None)
    decay_date: Optional[str] = Field(None)

    is_synthetic: int = Field(..., ge=0, le=1)
    propagation_minutes: float = Field(..., ge=0.0)

    rcs_size: Optional[str] = Field(None)
    country_code: Optional[str] = Field(None)

    # --- 2. Temporal Data ---
    epoch: str = Field(...)
    epoch_dt: datetime = Field(...)
    source_epoch: Optional[datetime] = None

    # --- 3. Base Orbital Elements (OMM/TLE) ---
    mean_motion: Optional[float] = None
    eccentricity: Optional[float] = None
    inclination: Optional[float] = None
    ra_of_asc_node: Optional[float] = None
    arg_of_pericenter: Optional[float] = None
    mean_anomaly: Optional[float] = None
    bstar: Optional[float] = None
    mean_motion_dot: Optional[float] = None
    mean_motion_ddot: Optional[float] = None
    semimajor_axis: Optional[float] = None

    # --- Physics Derived ---
    log_bstar: Optional[float] = None
    perigee_alt_km: Optional[float] = None
    calc_mean_motion_dot: Optional[float] = None

    # --- Cyclic ---
    sin_raan: Optional[float] = None
    cos_raan: Optional[float] = None
    sin_arg_per: Optional[float] = None
    cos_arg_per: Optional[float] = None
    sin_mean_anomaly: Optional[float] = None
    cos_mean_anomaly: Optional[float] = None

    # --- Spatio-temporal ---
    local_solar_time: Optional[float] = None
    cos_lst: Optional[float] = None

    # --- Targets (training only) ---
    rul_days: Optional[float] = None
    log_rul: Optional[float] = None

    # --- State Vector Derived (SGP4-based) ---
    speed_km_s: Optional[float] = Field(
        None, gt=0,
        description="Instantaneous orbital speed from SGP4 state vector")

    altitude_km: Optional[float] = Field(
        None,
        description="Altitude above Earth radius derived from position vector")

    radial_velocity_km_s: Optional[float] = Field(
        None,
        description="Velocity component along radial direction")

    tangential_velocity_km_s: Optional[float] = Field(
        None,
        description="Velocity component orthogonal to radial direction")

    flight_path_angle_rad: Optional[float] = Field(
        None,
        description="Angle between velocity vector and local horizontal plane")

    abs_propagation_minutes: Optional[float] = Field(
        None, ge=0,
        description="Absolute time offset from reference TLE")

    is_far_from_tle: Optional[bool] = Field(
        None,
        description="True if propagation offset exceeds safe threshold")