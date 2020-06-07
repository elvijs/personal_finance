import csv
from pathlib import Path
from typing import Mapping, Iterator

from enum import Enum

MAPPINGS_FILE = Path("../rules/mappings.csv")

ColumnValues = Mapping[str, str]


class Columns(Enum):
    long_desc_regex = "long_description_regex"
    short_desc = "short_description"
    bank_category = "bank_category"
    sub_category = "sub_category"
    category = "category"


def load_map(from_column: Columns, to_column: Columns) -> ColumnValues:
    return {
        row[from_column.value]: row[to_column.value]
        for row in _get_description_map_dicts()
        if row[from_column.value] and row[to_column.value]
    }


def _get_description_map_dicts() -> Iterator[ColumnValues]:
    with open(str(MAPPINGS_FILE), "r") as f:
        reader = csv.DictReader(f, delimiter=',')
        fieldnames = set(reader.fieldnames)
        expected_fieldnames = set(column.value for column in Columns)

        assert list(fieldnames) == list(expected_fieldnames)
        for row in reader:
            yield row
