from __future__ import annotations
from typing import List, Dict, Optional, Literal, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime
from enum import Enum


class SatelliteRecord(BaseModel):
    """
    Raw satellite orbital state from Space-Track OMM format.
    Preserves original types (Union[str, float]) - type coercion happens in Phase 2.
    """

    model_config = ConfigDict(frozen=True, extra='ignore', populate_by_name=True)

    object_name: Optional[str] = Field(None, alias="OBJECT_NAME")
    norad_cat_id: int = Field(..., gt=0, alias="NORAD_CAT_ID")  # TODO: check if we can use int32 instead

    # temporal fields
    epoch: str = Field(..., alias="EPOCH")
    creation_date: Optional[str] = Field(None, alias="CREATION_DATE")
    decay_date: Optional[str] = Field(None, alias="DECAY_DATE")

    mean_motion: Optional[Union[float, str]] = Field(None, alias="MEAN_MOTION")
    eccentricity: Optional[Union[float, str]] = Field(None, alias="ECCENTRICITY")
    inclination: Optional[Union[float, str]] = Field(None, alias="INCLINATION")
    ra_of_asc_node: Optional[Union[float, str]] = Field(None, alias="RA_OF_ASC_NODE")
    arg_of_pericenter: Optional[Union[float, str]] = Field(None, alias="ARG_OF_PERICENTER")
    mean_anomaly: Optional[Union[float, str]] = Field(None, alias="MEAN_ANOMALY")

    bstar: Optional[Union[float, str]] = Field(None, alias="BSTAR")
    mean_motion_dot: Optional[Union[float, str]] = Field(None, alias="MEAN_MOTION_DOT")
    mean_motion_ddot: Optional[Union[float, str]] = Field(None, alias="MEAN_MOTION_DDOT")

    rcs_size: Optional[str] = Field(None, alias="RCS_SIZE")
    country_code: Optional[str] = Field(None,alias="COUNTRY_CODE")

    semimajor_axis: Optional[Union[float, str]] = Field(None, alias="SEMIMAJOR_AXIS")
    period: Optional[Union[float, str]] = Field(None, alias="PERIOD")
    apoapsis: Optional[Union[float, str]] = Field(None, alias="APOAPSIS")
    periapsis: Optional[Union[float, str]] = Field(None, alias="PERIAPSIS")
    object_type: Optional[str] = Field(None, alias="OBJECT_TYPE")

    launch_date: Optional[str] = Field(None, alias="LAUNCH_DATE")
    rev_at_epoch: Optional[Union[int, str]] = Field(None, alias="REV_AT_EPOCH")

    tle_line0: Optional[str] = Field(None, alias="TLE_LINE0")
    tle_line1: Optional[str] = Field(None, alias="TLE_LINE1")
    tle_line2: Optional[str] = Field(None, alias="TLE_LINE2")