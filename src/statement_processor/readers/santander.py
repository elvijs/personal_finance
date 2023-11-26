import csv
import datetime
import enum
import logging
import re
from pathlib import Path
from typing import Tuple, Sequence, Optional, Generator, Mapping

from statement_processor.models import Statement, Transaction
from statement_processor.readers.api import StatementReader, ParsedValue, FromToValue
from statement_processor.utils import normalize, parse_date, parse_float

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

    def process(self) -> Statement:
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


class CreditCardColumn(str, enum.Enum):
    CARD_NO = "Card no."
    DATE = "Date"
    DESCRIPTION = "Description"
    MONEY_IN = "Money in"
    MONEY_OUT = "Money out"


class SantanderCreditCardStatementReader(StatementReader):
    DELIMITER = "\t"
    DATE_FORMATS = ["%Y-%m-%d"]
    CARD_NUMBER_LAST_DIGITS = "9976"  # for validation
    ACCOUNT_ID = "santander_credit_card_xx_9976"

    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._path = path
        self._encoding = encoding

    def _filtered_input(self) -> Generator[str, None, None]:
        """Deal with Santander file messiness."""
        with self._path.open("r", encoding=self._encoding) as input_file:
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

    def process(self) -> Statement:
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
            self.ACCOUNT_ID,
            transactions,
        )

    def _create_transaction(self, row: Mapping[str, str]) -> Transaction:
        c = CreditCardColumn
        if row[c.CARD_NO]:
            card_num = row[c.CARD_NO][-4:]
            msg = "unexpected card number: {}".format(card_num)
            assert card_num == self.CARD_NUMBER_LAST_DIGITS, msg

        return Transaction(
            date=parse_date(row[c.DATE], supported_formats=self.DATE_FORMATS),
            description=row[c.DESCRIPTION],
            amount=-parse_float(row[c.MONEY_IN])
            if row[c.MONEY_IN]
            else parse_float(row[c.MONEY_OUT]),
            account_id=self.ACCOUNT_ID,
        )
