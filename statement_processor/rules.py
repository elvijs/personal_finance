import csv
import os
from pathlib import Path
from typing import Mapping, Iterator, Set

from enum import Enum

_this_file = os.path.realpath(__file__)
rule_map_file = Path(_this_file).parent.parent / "rules/mappings.csv"
ignored_transactions_file = (
    Path(_this_file).parent.parent / "rules/ignored_transactions.csv"
)

EXPECTED_IGNORED_TRANSACTION_RULES = ["type", "description"]

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
    with rule_map_file.open("r") as f:
        reader = csv.DictReader(f, delimiter=',')
        fieldnames = set(reader.fieldnames)
        expected_fieldnames = set(column.value for column in Columns)

        assert list(fieldnames) == list(expected_fieldnames)
        for row in reader:
            yield row


def get_ignore_rules(type_: str) -> Set[str]:
    with ignored_transactions_file.open("r") as f:
        reader = csv.DictReader(f, delimiter=',')
        assert list(reader.fieldnames) == EXPECTED_IGNORED_TRANSACTION_RULES
        result = {row["description"] for row in reader if row["type"] == type_}
    return result
