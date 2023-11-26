import csv
from enum import Enum
from pathlib import Path
from typing import Mapping

from statement_processor.models import Statement, Transaction
from statement_processor.readers.api import StatementReader
from statement_processor.utils import parse_date, normalize, parse_float


class Column(str, Enum):
    DATE = "Completed Date"
    STARTED_DATE = "Started Date"
    DESCRIPTION = "Description"
    REFERENCE = "Reference"
    PAID = "Paid Out (GBP)"
    RECEIVED = "Paid In (GBP)"
    AMOUNT = "Amount"


class RevolutStatementReader(StatementReader):
    DELIMITERS = [";", ","]
    DATE_FORMATS = ["%d %b %Y", "%Y-%m-%d %H:%M:%S"]
    ACCOUNT_ID = "revolut"

    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._path = path
        self._encoding = encoding

    def process(self) -> Statement:
        caught_exceptions = []

        for delimiter in self.DELIMITERS:
            try:
                return self._get_statement_with_delimiter(delimiter)
            except KeyError as ex:  # the wrong delimiter will result in one column
                caught_exceptions.append(ex)
                continue

        raise ValueError(
            f"Could not read the statement. "
            f"Caught the following exceptions: {caught_exceptions}"
        )

    def _get_statement_with_delimiter(self, delimiter: str) -> Statement:
        with self._path.open("r", encoding=self._encoding) as input_file:
            reader = csv.DictReader(input_file, delimiter=delimiter)

            transactions = []
            for row in reader:
                transactions.append(self._create_transaction(row))

        return Statement(
            min([t.date for t in transactions]),
            max([t.date for t in transactions]),
            self.ACCOUNT_ID,
            transactions,
        )

    def _create_transaction(self, row: Mapping[str, str]) -> Transaction:
        row = self._normalize_row(row)
        c = Column
        raw_date = row[c.DATE] if row[c.DATE] else row[c.STARTED_DATE]
        date = parse_date(raw_date, supported_formats=self.DATE_FORMATS)
        raw_description = row.get(c.DESCRIPTION, row.get(c.REFERENCE, ""))
        description = normalize(raw_description)
        amount = self._get_amount(row)
        return Transaction(date, description, amount, self.ACCOUNT_ID)

    @staticmethod
    def _get_amount(row: Mapping[str, str]) -> float:
        c = Column
        if row.get(c.PAID):
            return parse_float(row[c.PAID])
        elif row.get(c.AMOUNT):
            return -parse_float(row[c.AMOUNT])
        else:
            return -parse_float(row[c.RECEIVED])

    @staticmethod
    def _normalize_row(row: Mapping[str, str]) -> Mapping[str, str]:
        return {normalize(k): normalize(v) for k, v in row.items()}
