
from abc import ABC, abstractmethod
import polars as pl
from typing import Tuple, List, Any

class BaseDataProcessor(ABC):

    def process(self, raw_text: str) -> pl.DataFrame:

        lines = self._prepare_input(raw_text)
        records, skipped = self._iterate_and_parse(lines)

        df = self._create_dataframe(records)
        df = self._validate_output(df)

        return df

    def _iterate_and_parse(
        self,
        lines: List[str],
    ) -> Tuple[List[Any], int]:

        processed, skipped = [], 0

        for line in lines:
            try:
                record = self._parse_line(line)
                if record is not None:
                    processed.append(record)
                else:
                    skipped += 1
            except (ValueError, TypeError):
                skipped += 1

        return processed, skipped

    @abstractmethod
    def _prepare_input(self, raw_text: str) -> List[str]:
        pass

    @abstractmethod
    def _parse_line(self, line: str):
        pass

    @abstractmethod
    def _create_dataframe(self, records: List[Any]) -> pl.DataFrame:
        pass

    def _validate_output(self, df: pl.DataFrame) -> pl.DataFrame:
        return df