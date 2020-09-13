import csv
import os
from enum import Enum
from pathlib import Path
from typing import Iterator, Mapping, Set, Optional

_this_file = os.path.realpath(__file__)
_rules_dir = os.environ.get("RULES_DIR")
if not _rules_dir:
    _rules_dir = Path(_this_file).parent.parent / "rules"
else:
    _rules_dir = Path(_rules_dir)

assert _rules_dir.exists(), \
    f"{_rules_dir} does not exist. " \
    f"Please provide a 'mapping.csv' and 'ignored_transactions.csv' at this location" \
    f"or set the RULES_DIR environment variable"

rule_map_file = _rules_dir / "mappings.csv"
ignored_transactions_file = _rules_dir / "ignored_transactions.csv"


class IgnoredTransactionColumn(Enum):
    type = "type"
    description = "description"


class IgnoredTransactionType(Enum):
    full = "full"
    # Transaction descriptions matching this message in full will be ignored
    partial = "partial"
    # Transaction descriptions containing this message will be ignored


ColumnValues = Mapping[str, str]


class MappingRuleColumn(Enum):
    long_desc_regex = "long_description_regex"
    short_desc = "short_description"
    bank_category = "bank_category"
    sub_category = "sub_category"
    category = "category"


def load_map(
    from_column: MappingRuleColumn, to_column: MappingRuleColumn
) -> ColumnValues:
    return {
        row[from_column.value]: row[to_column.value]
        for row in _get_description_map_dicts()
        if row[from_column.value] and row[to_column.value]
    }


def _get_description_map_dicts() -> Iterator[ColumnValues]:
    with rule_map_file.open("r") as f:
        reader = csv.DictReader(f, delimiter=",")
        assert reader.fieldnames, f"Expected the rules map to have column headers"
        fieldnames = set(reader.fieldnames)
        expected_fieldnames = set(column.value for column in MappingRuleColumn)

        assert list(fieldnames) == list(expected_fieldnames)
        for row in reader:
            yield row


def get_ignore_rules(type_: IgnoredTransactionType) -> Set[str]:
    with ignored_transactions_file.open("r") as f:
        reader = csv.DictReader(f, delimiter=",")
        assert reader.fieldnames, \
            f"Expected the ignore rules map to have column headers"

        assert list(reader.fieldnames) == [
            IgnoredTransactionColumn.type.value,
            IgnoredTransactionColumn.description.value,
        ]
        result = {row["description"] for row in reader if row["type"] == type_.value}
    return result
