import polars as pl
from datetime import datetime

from structlog.stdlib import BoundLogger
from typing import Dict, Any, Type, Union, get_origin, get_args, List
from src.domain.contracts.orbital_features_schema import OrbitMainType, DecayRiskLevel
from src.domain.orbital.features.models.enriched_record import EnrichedOrbitRecord

from enum import Enum

class FeatureRecordValidator:
    """
    Columnar validator for Phase 3 feature engineering.
    Builds validation rules from EnrichedOrbitRecord schema and applies them via Polars.
    """

    PYDANTIC_TO_POLARS: Dict[Type, pl.DataType] = {
        int: pl.Int64(),
        float: pl.Float64(),
        str: pl.String(),
        bool: pl.Boolean(),
        datetime: pl.Datetime(),
    }

    def __init__(self, logger: BoundLogger) -> None:
        self.logger = logger
        self.rules = self._extract_schema_rules()
        self.dtype_map = self._extract_dtypes()
        self.enum_constraints = self._extract_enum_values()

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Validates features via structure check, type casting, and constraint enforcement.
        Returns filtered DataFrame with invalid rows removed.
        """
        if df.is_empty():
            return df

        self._enforce_schema_structure(df)

        initial_count = df.height

        try:
            df = df.cast(self.dtype_map, strict=False)
        except Exception as e:
            self.logger.error("schema_type_cast_error", error=str(e))

        df = self._apply_domain_constraints(df)

        df = df.drop_nulls(subset=self.rules["required"])

        removed = initial_count - df.height
        if removed > 0:
            self.logger.warning(
                "features_filtered_by_validator",
                removed_count=removed,
                remaining=df.height,
                reason="out_of_bounds_or_schema_mismatch")

        return df

    def _extract_dtypes(self) -> Dict[str, pl.DataType]:
        """Extracts Polars dtype map from EnrichedOrbitRecord schema."""
        dtype_map = {}

        for name, field_info in EnrichedOrbitRecord.model_fields.items():
            py_type = field_info.annotation

            if get_origin(py_type) is Union:
                args = get_args(py_type)
                for arg in args:
                    if arg is not type(None):
                        py_type = arg
                        break

            if isinstance(py_type, type) and issubclass(py_type, Enum):
                pl_type = pl.String()
            else:
                pl_type = self.PYDANTIC_TO_POLARS.get(py_type, pl.String())

            dtype_map[name] = pl_type

        return dtype_map

    def _extract_schema_rules(self) -> Dict[str, Any]:
        """Extracts validation rules from Pydantic Field metadata (ge, le, etc)."""
        required_fields = []
        range_constraints = []

        for name, field_info in EnrichedOrbitRecord.model_fields.items():
            if field_info.is_required():
                required_fields.append(name)

            constraints = {}
            for metadata in field_info.metadata:
                if hasattr(metadata, 'ge'): constraints['ge'] = metadata.ge
                if hasattr(metadata, 'le'): constraints['le'] = metadata.le
                if hasattr(metadata, 'gt'): constraints['gt'] = metadata.gt
                if hasattr(metadata, 'lt'): constraints['lt'] = metadata.lt

            if constraints:
                range_constraints.append((name, constraints))

        return {
            "required": required_fields,
            "ranges": range_constraints
        }

    def _extract_enum_values(self) -> Dict[str, List[str]]:
        """Extracts allowed values for enum-based fields."""
        enum_map = {}
        for name, field_info in EnrichedOrbitRecord.model_fields.items():
            py_type = field_info.annotation

            if get_origin(py_type) is Union:
                args = get_args(py_type)
                for arg in args:
                    if arg is not type(None):
                        py_type = arg
                        break

            if isinstance(py_type, type) and issubclass(py_type, (OrbitMainType, DecayRiskLevel)):
                enum_values = [e.value for e in py_type]
                enum_map[name] = enum_values

        return enum_map

    def _apply_domain_constraints(self, df: pl.DataFrame) -> pl.DataFrame:
        """Applies range and enum constraints via Polars expressions."""
        expressions = []

        for col_name, constraints in self.rules["ranges"]:
            if col_name not in df.columns:
                continue

            col_expr = pl.col(col_name)
            is_valid = pl.lit(True)

            if 'ge' in constraints: is_valid &= (col_expr >= constraints['ge'])
            if 'le' in constraints: is_valid &= (col_expr <= constraints['le'])
            if 'gt' in constraints: is_valid &= (col_expr > constraints['gt'])
            if 'lt' in constraints: is_valid &= (col_expr < constraints['lt'])

            expressions.append(col_expr.is_null() | is_valid)

        for col_name, allowed_values in self.enum_constraints.items():
            if col_name in df.columns:
                col_expr = pl.col(col_name)
                expressions.append(
                    col_expr.is_null() | col_expr.is_in(allowed_values))

        if not expressions:
            return df

        combined_mask = pl.all_horizontal(expressions)
        return df.filter(combined_mask)

    def _enforce_schema_structure(self, df: pl.DataFrame) -> None:
        """Validates presence of required columns, raises if missing."""
        required_set = set(self.rules["required"])
        columns_set = set(df.columns)
        missing = required_set - columns_set

        if missing:
            self.logger.critical(
                "feature_schema_violation",
                missing_columns=list(missing))
            raise RuntimeError(f"Missing required columns in feature data: {missing}")