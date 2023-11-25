import csv
import datetime
import enum
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union, Generator, Mapping

from statement_processor.models import Transaction, Statement
from statement_processor.utils import parse_float, normalize, parse_date

FromToValue = Tuple[datetime.date, datetime.date]
AccountValue = str
DateValue = datetime.date
DescriptionValue = str
AmountValue = float
BalanceValue = float

ParsedValue = Union[
    FromToValue,
    AccountValue,
    DateValue,
    DescriptionValue,
    AmountValue,
    BalanceValue,
]

StartEnd = Tuple[datetime.date, datetime.date]

LOG = logging.getLogger(__file__)


class InputFileTokens(enum.Enum):
    """Tokens found in Santander TXT versions of statements"""

    FromTo = "From"
    Account = "Account"
    Date = "Date"
    Description = "Description"
    Amount = "Amount"
    Balance = "Balance"


TokenizedLine = Tuple[InputFileTokens, ParsedValue]


class StatementReader(ABC):
    @abstractmethod
    def get_statement(self) -> Statement:
        """Get a statement representing the file's contents"""

    @staticmethod
    def _validate_statement_path(path: Path) -> None:
        """We expect statements to be stored at e.g. .../2023/September/..."""
        year = int(path.parent.parent.name)
        month = path.parent.name
        datetime.datetime.strptime(f"{year}-{month}", "%Y-%B")


class SantanderBankStatementReader(StatementReader):
    TOKEN_SEPARATOR = ":"
    SUPERFLUOUS_CHARACTERS = "/t/n"
    DATE_FORMATS = ["%d/%m/%Y"]
    DATE_SPLITTER = "to"

    ACCOUNT_ID_MAP = {
        "42564627": "santander_basic",
        "83154494": "santander_everyday",
        "17254953": "santander_123_current_account",
    }

    def __init__(self, path: Path, encoding: str = "iso-8859-15") -> None:
        self._path = path
        self._validate_statement_path(path)
        self._encoding = encoding

        self._account_id = self._get_account_id()

    def _get_account_id(self) -> str:
        # get a nice account id
        for k, v in self.ACCOUNT_ID_MAP.items():
            if k in self._path.stem:
                return v

        raise ValueError(
            f"Did not find any of the account IDs {self.ACCOUNT_ID_MAP.keys()} "
            f"in the file name '{self._path}'"
        )

    def get_statement(self) -> Statement:
        tokenized_lines = self._get_tokenized_and_parsed_lines()

        # Help out MyPy
        assert tokenized_lines[0][0] == InputFileTokens.FromTo
        assert isinstance(tokenized_lines[0][1], tuple)
        from_date, to_date = tokenized_lines[0][1]

        assert tokenized_lines[1][0] == InputFileTokens.Account

        transactions = []
        for i in range(2, len(tokenized_lines), 4):
            date, description, amount, balance = tokenized_lines[i : i + 4]
            # Help out MyPy
            assert isinstance(date[1], datetime.date)
            assert isinstance(description[1], str)
            assert isinstance(amount[1], float)
            transaction = Transaction(
                date[1], description[1], -amount[1], self._account_id
            )
            transactions.append(transaction)

        return Statement(
            from_date,
            to_date,
            self._account_id,
            transactions,
        )

    def _get_tokenized_and_parsed_lines(self) -> Sequence[TokenizedLine]:
        with self._path.open("r", encoding=self._encoding) as input_file:
            tokenized_and_parsed_lines = []
            for line in input_file:
                tokenized = self._tokenize_line(line)
                if not tokenized:
                    continue
                token, raw_value = tokenized
                parsed_value = self._parse_value(token, raw_value)
                tokenized_and_parsed_lines.append((token, parsed_value))

        return tokenized_and_parsed_lines

    def _tokenize_line(self, line: str) -> Optional[Tuple[InputFileTokens, str]]:
        split_line = line.split(self.TOKEN_SEPARATOR)
        if len(split_line) <= 1:
            return None

        for potential_token in InputFileTokens:
            if potential_token.value == split_line[0]:
                return potential_token, ":".join(split_line[1:])

        raise ValueError(f"Unrecognised token on line: {line}")

    # TODO: types can be made stricter via typing.overload decorator
    def _parse_value(self, token: InputFileTokens, raw_value: str) -> ParsedValue:
        if token == InputFileTokens.FromTo:
            return self._parse_from_to_token(raw_value)
        elif token == InputFileTokens.Account:
            return normalize(raw_value)
        elif token == InputFileTokens.Date:
            return parse_date(normalize(raw_value), supported_formats=self.DATE_FORMATS)
        elif token == InputFileTokens.Description:
            return normalize(raw_value)
        elif token == InputFileTokens.Amount:
            return parse_float(raw_value)
        elif token == InputFileTokens.Balance:
            return parse_float(raw_value)
        else:
            raise ValueError(f"Could not parse token {token} with value {raw_value}")

    def _parse_from_to_token(self, raw_value: str) -> FromToValue:
        normalized_value = normalize(raw_value)
        value = re.sub(r"\s", "", normalized_value)

        date_strings = value.split(self.DATE_SPLITTER)
        return (
            parse_date(date_strings[0], supported_formats=self.DATE_FORMATS),
            parse_date(date_strings[1], supported_formats=self.DATE_FORMATS),
        )


class RevolutStatementReader(StatementReader):
    DELIMITERS = [";", ","]
    DATE_FORMATS = ["%d %b %Y", "%Y-%m-%d %H:%M:%S"]
    ACCOUNT_ID = "revolut"

    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._path = path
        self._validate_statement_path(path)
        self._encoding = encoding

    def get_statement(self) -> Statement:
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
            "Revolut card",
            transactions,
        )

    def _create_transaction(self, row: Mapping[str, str]) -> Transaction:
        row = self._normalize_row(row)
        # TODO: move column names into an enum
        raw_date = (
            row["Completed Date"] if row["Completed Date"] else row["Started Date"]
        )
        date = parse_date(raw_date, supported_formats=self.DATE_FORMATS)
        raw_description = row.get("Description", row.get("Reference", ""))
        description = normalize(raw_description)
        amount = self._get_amount(row)
        return Transaction(date, description, amount, self.ACCOUNT_ID)

    @staticmethod
    def _get_amount(row: Mapping[str, str]) -> float:
        # TODO: column names should be in an enum
        if row.get("Paid Out (GBP)"):
            return parse_float(row["Paid Out (GBP)"])
        elif row.get("Amount"):
            return -parse_float(row["Amount"])
        else:
            return -parse_float(row["Paid In (GBP)"])

    @staticmethod
    def _normalize_row(row: Mapping[str, str]) -> Mapping[str, str]:
        return {normalize(k): normalize(v) for k, v in row.items()}


class SantanderCreditCardStatementReader(StatementReader):
    DELIMITER = "\t"
    DATE_FORMATS = ["%Y-%m-%d"]
    CARD_NUMBER_LAST_DIGITS = "9976"  # for validation
    ACCOUNT_ID = "santander_credit_card"

    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._path = path
        self._validate_statement_path(path)
        self._encoding = encoding

    def _filtered_input(self) -> Generator[str, None, None]:
        """Deal with Santander file messiness."""
        with open(self._path, "r", encoding=self._encoding) as input_file:
            for i, row in enumerate(input_file):
                if i == 0:
                    card_num = row[-5:-1]
                    msg = "unexpected card number: {}".format(card_num)
                    assert card_num == self.CARD_NUMBER_LAST_DIGITS, msg
                    continue  # skip over the first row
                elif re.sub("-", "", row) in ["\n", ""]:
                    continue  # skip over a delimiting row

                # Cleanup their ridiculous whitespace usage
                if i == 1:  # due to 'continue', this is the column name row
                    row = re.sub("\t+", "\t", row)

                cleanup1 = re.sub("\t\t", "\t", row)
                cleanup2 = re.sub("[ ]+", " ", cleanup1)
                yield cleanup2

    def get_statement(self) -> Statement:
        reader = csv.DictReader(self._filtered_input(), delimiter=self.DELIMITER)
        transactions = []
        for row in reader:
            try:
                transaction = self._create_transaction(row)
                transactions.append(transaction)
            except Exception as ex:
                LOG.info("Issue creating a transaction from row: {}".format(row))
                raise ex

        return Statement(
            min([t.date for t in transactions]),
            max([t.date for t in transactions]),
            "Santander credit card",
            transactions,
        )

    @staticmethod
    def _clean_description(description: str) -> str:
        return normalize(re.sub("PURCHASE - DOMESTIC", "", description))

    def _create_transaction(self, row: Mapping[str, str]) -> Transaction:
        if row["Card no."]:
            card_num = row["Card no."][-4:]
            msg = "unexpected card number: {}".format(card_num)
            assert card_num == self.CARD_NUMBER_LAST_DIGITS, msg

        return Transaction(
            date=parse_date(row["Date"], supported_formats=self.DATE_FORMATS),
            description=self._clean_description(row["Description"]),
            amount=-parse_float(row["Money in"])
            if row["Money in"]
            else parse_float(row["Money out"]),
            account_id=self.ACCOUNT_ID,
        )
