
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProcessedOrbitRecord(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra='ignore',
        populate_by_name=True)

    # --- 1. Identity & Metadata ---
    norad_cat_id: int = Field(...)
    segment_id: str = Field(...)

    object_type: str = Field(...)
    launch_date: str = Field(...)
    creation_date: str = Field(...)
    decay_date: str = Field(...)

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

    ref_mean_motion: Optional[float] = Field(None, description="Original Mean Motion from TLE")
    ref_eccentricity: Optional[float] = Field(None, description="Original Eccentricity from TLE")
    ref_inclination: Optional[float] = Field(None, description="Original Inclination from TLE")
    ref_ra_of_asc_node: Optional[float] = Field(None, description="Original RAAN from TLE")
    ref_arg_of_pericenter: Optional[float] = Field(None, description="Original Arg of Perigee from TLE")
    ref_mean_anomaly: Optional[float] = Field(None, description="Original Mean Anomaly from TLE")
    ref_bstar: Optional[float] = Field(None, description="Drag Term")
    ref_mean_motion_dot: Optional[float] = Field(None, description="Ballistic Coefficient")
    ref_mean_motion_ddot: Optional[float] = Field(None, description="Second Derivative of Mean Motion")
    ref_semimajor_axis: Optional[float] = Field(None, description="Original Semi-Major Axis from TLE")

    # --- 6. Cartesian State (SGP4 output) ---
    pos_x: Optional[float] = Field(None, description="ECI X position [km]")
    pos_y: Optional[float] = Field(None, description="ECI Y position [km]")
    pos_z: Optional[float] = Field(None, description="ECI Z position [km]")

    vel_x: Optional[float] = Field(None, description="ECI X velocity [km/s]")
    vel_y: Optional[float] = Field(None, description="ECI Y velocity [km/s]")
    vel_z: Optional[float] = Field(None, description="ECI Z velocity [km/s]")



