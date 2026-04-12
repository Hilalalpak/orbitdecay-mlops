import polars as pl
from datetime import datetime
from structlog.stdlib import BoundLogger
from typing import Dict, Any, get_origin, get_args, Type, Union
from src.domain.orbital.processing.models.processed_record import ProcessedOrbitRecord


class OrbitRecordValidator:
    """
    Columnar validator for processed orbital records.
    Builds validation rules from ProcessedOrbitRecord schema and applies via Polars.
    """

    PYDANTIC_TO_POLARS: Dict[Type, pl.DataType] = {
        int: pl.Int64(),
        float: pl.Float64(),
        str: pl.String(),
        bool: pl.Boolean(),
        datetime: pl.Datetime("us")
    }

    def __init__(self, logger: BoundLogger) -> None:
        self.logger = logger
        self.rules = self._extract_schema_rules()
        self.dtype_map = self._extract_dtypes()

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.is_empty():
            return df

        self._enforce_schema_structure(df)

        initial_count = df.height

        try:
            df = df.cast(self.dtype_map)
        except Exception as e:
            self.logger.critical("schema_type_mismatch", error=str(e))
            raise RuntimeError(f"Data type mismatch with schema: {e}")

        df = df.drop_nulls(self.rules["required"])
        df = self._apply_domain_constraints(df)

        allowed_columns = list(self.dtype_map.keys())
        df = df.select(allowed_columns)

        removed = initial_count - df.height
        if removed > 0:
            self.logger.debug(
                "records_filtered_by_validator",
                removed=removed,
                remaining=df.height)

        return df

    def _extract_dtypes(self) -> Dict[str, pl.DataType]:
        """Maps Pydantic field types to Polars dtypes, handling Optional types."""
        dtype_map = {}

        for name, field_info in ProcessedOrbitRecord.model_fields.items():
            py_type = field_info.annotation

            if get_origin(py_type) is Union:
                args = get_args(py_type)
                for arg in args:
                    if arg is not type(None):
                        py_type = arg
                        break

            pl_type = self.PYDANTIC_TO_POLARS.get(py_type)

            if pl_type:
                dtype_map[name] = pl_type

        return dtype_map

    def _enforce_schema_structure(self, df: pl.DataFrame) -> None:
        """Validates presence of required schema fields, raises if missing."""
        required_set = set(self.rules["required"])
        columns_set = set(df.columns)

        missing_columns = required_set - columns_set

        if missing_columns:
            self.logger.critical(
                "schema_contract_violation",
                missing_columns=list(missing_columns),
                reason="Processor failed to generate required fields")
            raise RuntimeError(
                f"Validation Failed: Processor output is missing required schema fields: {missing_columns}")

    def _extract_schema_rules(self) -> Dict[str, Any]:
        """Introspects Pydantic model to find required fields and constraints."""
        required_fields = []
        range_constraints = []

        for name, field_info in ProcessedOrbitRecord.model_fields.items():
            if field_info.is_required():
                required_fields.append(name)

            constraints = {}
            for metadata in field_info.metadata:
                if hasattr(metadata, 'ge'): constraints['ge'] = metadata.ge  # Greater or Equal
                if hasattr(metadata, 'le'): constraints['le'] = metadata.le  # Less or Equal
                if hasattr(metadata, 'gt'): constraints['gt'] = metadata.gt  # Greater Than
                if hasattr(metadata, 'lt'): constraints['lt'] = metadata.lt  # Less Than

            if constraints:
                range_constraints.append((name, constraints))

        self.logger.debug(
            "schema_rules_extracted",
            required=required_fields,
            ranges=[name for name, _ in range_constraints])

        return {
            "required": required_fields,
            "ranges": range_constraints
        }

    def _apply_domain_constraints(self, df: pl.DataFrame) -> pl.DataFrame:
        """Applies dynamic range constraints using Polars expressions."""
        expressions = []

        for col_name, constraints in self.rules["ranges"]:
            if col_name not in df.columns:
                continue

            col_expr = pl.col(col_name)

            if 'ge' in constraints: expressions.append(col_expr >= constraints['ge'])
            if 'le' in constraints: expressions.append(col_expr <= constraints['le'])
            if 'gt' in constraints: expressions.append(col_expr > constraints['gt'])
            if 'lt' in constraints: expressions.append(col_expr < constraints['lt'])

        if not expressions:
            return df

        combined_mask = pl.all_horizontal(expressions)
        return df.filter(combined_mask)