import csv
import datetime
import decimal
import enum
import logging
import re
import unicodedata
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import IO, Optional, Sequence, Tuple, Union

from dateutil.relativedelta import relativedelta

from statement_processor.statements import Statement
from statement_processor.transactions import Transaction

FromToValue = Tuple[datetime.date, datetime.date]
AccountValue = str
DateValue = datetime.date
DescriptionValue = str
AmountValue = decimal.Decimal
BalanceValue = decimal.Decimal

ParsedValue = Union[
    FromToValue, AccountValue, DateValue, DescriptionValue, AmountValue, BalanceValue,
]

StartEnd = Tuple[datetime.date, datetime.date]


class InputFileTokens(enum.Enum):
    """ Tokens found in Santander TXT versions of statements """

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
        """ Get a statement representing the file's contents """

    def _get_statement_start_and_end(self, path: str) -> StartEnd:
        """ Deconstruct the path to provide the statement start and end. """
        matches = re.search(r"/[0-9]{4}/[a-zA-Z]{3,9}/", path)
        start = datetime.datetime.strptime(matches.group(0), "/%Y/%B/")
        # strptime defaults to the first day of month
        end = start + relativedelta(months=1, days=-1)
        return start.date(), end.date()

    def _parse_date(self, date: str, supported_formats: Sequence[str]) -> datetime.date:
        for potential_format in supported_formats:
            try:
                return datetime.datetime.strptime(date, potential_format).date()
            except ValueError:
                continue

        raise ValueError(
            f"Date {date} does not match any of "
            f"the expected formats: {supported_formats}",
        )

    @staticmethod
    def _normalize(raw_value: str) -> str:
        try:
            return unicodedata.normalize("NFKD", raw_value).strip()
        except TypeError:
            # TODO: log errors?
            return raw_value

    def _parse_decimal(self, value: str) -> decimal.Decimal:
        try:
            return decimal.Decimal(self._normalize(value).strip())
        except decimal.InvalidOperation:
            return decimal.Decimal(self._normalize(value.replace(",", "")).strip())


class SantanderBankStatementReader(StatementReader):
    ENCODING = "iso-8859-15"
    TOKEN_SEPARATOR = ":"
    SUPERFLUOUS_CHARACTERS = "/t/n"
    DATE_FORMATS = ["%d/%m/%Y"]
    DATE_SPLITTER = "to"

    def __init__(self, path: str, encoding: str = None) -> None:
        self._path = path  # TODO: validate path
        self._encoding = encoding or self.ENCODING

    def get_statement(self) -> Statement:
        tokenized_lines = self._get_tokenized_and_parsed_lines()

        assert tokenized_lines[0][0] == InputFileTokens.FromTo
        from_date = tokenized_lines[0][1][0]
        to_date = tokenized_lines[0][1][1]

        assert tokenized_lines[1][0] == InputFileTokens.Account
        account = tokenized_lines[1][1]

        transactions = []
        for i in range(2, len(tokenized_lines), 4):
            date, description, amount, balance = tokenized_lines[i : i + 4]
            transaction = Transaction(date[1], description[1], -amount[1], balance[1])
            transactions.append(transaction)

        return Statement(from_date, to_date, account, transactions)

    def _get_tokenized_and_parsed_lines(self) -> Sequence[TokenizedLine]:
        with open(self._path, "r", encoding=self._encoding) as input_file:
            tokenized_and_parsed_lines = []
            for line in input_file:
                token, raw_value = self._tokenize_line(line)
                if not token:
                    continue
                parsed_value = self._parse_value(token, raw_value)
                tokenized_and_parsed_lines.append((token, parsed_value))

        return tokenized_and_parsed_lines

    def _tokenize_line(self, line: str) -> Optional[InputFileTokens]:
        split_line = line.split(self.TOKEN_SEPARATOR)
        if len(split_line) <= 1:
            return None, None

        for potential_token in InputFileTokens:
            if potential_token.value == split_line[0]:
                return potential_token, ":".join(split_line[1:])

        raise Exception("Unexpected token on line: {}".format(line))
        # TODO: specialize the exception

    # TODO: types can be made stricter via typing.overload decorator
    def _parse_value(self, token: InputFileTokens, raw_value: str) -> ParsedValue:
        if token == InputFileTokens.FromTo:
            return self._parse_from_to_token(raw_value)
        elif token == InputFileTokens.Account:
            return self._normalize(raw_value)
        elif token == InputFileTokens.Date:
            return self._parse_date(self._normalize(raw_value), supported_formats=self.DATE_FORMATS)
        elif token == InputFileTokens.Description:
            return self._normalize(raw_value)
        elif token == InputFileTokens.Amount:
            return self._parse_decimal(raw_value)
        elif token == InputFileTokens.Balance:
            return self._parse_decimal(raw_value)
        else:
            raise Exception(
                "Could not parse token {} with " "value {}".format(token, raw_value)
            )
        # TODO: specialize the exception

    def _parse_from_to_token(self, raw_value: str) -> FromToValue:
        normalized_value = self._normalize(raw_value)
        value = re.sub("\s", "", normalized_value)

        date_strings = value.split(self.DATE_SPLITTER)
        return (
            self._parse_date(date_strings[0], supported_formats=self.DATE_FORMATS),
            self._parse_date(date_strings[1], supported_formats=self.DATE_FORMATS),
        )


class RevolutStatementReader(StatementReader):
    ENCODING = "utf-8"
    DELIMITERS = [";", ","]
    DATE_FORMATS = ["%d %b %Y", "%Y-%m-%d %H:%M:%S"]

    def __init__(self, path: str, encoding: str = None) -> None:
        self._path = path  # TODO: validate path
        self._encoding = encoding or self.ENCODING

    def get_statement(self) -> Statement:
        caught_exceptions = []

        for delimiter in self.DELIMITERS:
            try:
                return self._get_statement_with_delimiter(delimiter)
            except KeyError as ex:  # the wrong delimiter will result in one column
                caught_exceptions.append(ex)
                continue

        raise Exception(
            f"Could not read the statement. "
            f"Caught the following exceptions: {caught_exceptions}"
        )

    def _get_statement_with_delimiter(self, delimiter: str) -> Statement:
        with open(self._path, "r", encoding=self._encoding) as input_file:
            reader = csv.DictReader(input_file, delimiter=delimiter)

            transactions = []
            for row in reader:
                transactions.append(self._create_transaction(row))

        from_date, to_date = self._get_statement_start_and_end(self._path)

        return Statement(from_date, to_date, "Revolut card", transactions)

    def _create_transaction(self, row: OrderedDict) -> Transaction:
        row = self._normalize_row(row)
        # TODO: move column names into an enum
        raw_date = row["Completed Date"] if row["Completed Date"] else row["Started Date"]
        date = self._parse_date(raw_date, supported_formats=self.DATE_FORMATS)
        raw_description = row.get("Description", row.get("Reference", None))
        description = self._normalize(raw_description)
        amount = self._get_amount(row)
        raw_balance = row.get("Balance (GBP)", row.get("Balance", None))
        balance = self._parse_decimal(raw_balance) if raw_balance else None
        bank_category = self._normalize(row.get("Category", None))
        return Transaction(date, description, amount, balance, bank_category)

    def _get_amount(self, row: OrderedDict) -> decimal.Decimal:
        # TODO: column names should be in an enum
        if row.get("Paid Out (GBP)"):
            return self._parse_decimal(row["Paid Out (GBP)"])
        elif row.get("Amount"):
            return -self._parse_decimal(row["Amount"])
        else:
            return -self._parse_decimal(row["Paid In (GBP)"])

    def _normalize_row(self, row: OrderedDict) -> OrderedDict:
        ret = OrderedDict()
        for k, v in row.items():
            ret[self._normalize(k)] = self._normalize(v)
        return ret


def _print_tabs(s: str):
    print(re.sub("\t", "TAB", s))


class SantanderCreditCardStatementReader(StatementReader):
    ENCODING = "utf-8"
    DELIMITER = "\t"
    DATE_FORMATS = ["%Y-%m-%d"]
    CARD_NUMBER_LAST_DIGITS = "9976"  # for validation

    def __init__(self, path: str, encoding: str = None) -> None:
        self._path = path  # TODO: validate path
        self._encoding = encoding or self.ENCODING

    def _filtered_input(self) -> IO[str]:
        """ Deal with Santander file messiness. """
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
                # _print_tabs(row)
                if i == 1:  # due to 'continue', this is the column name row
                    row = re.sub("\t+", "\t", row)

                cleanup1 = re.sub("\t\t", "\t", row)
                cleanup2 = re.sub("[ ]+", " ", cleanup1)
                # _print_tabs(cleanup2)
                yield cleanup2

    def get_statement(self) -> Statement:
        reader = csv.DictReader(self._filtered_input(), delimiter=self.DELIMITER)
        from_date, to_date = self._get_statement_start_and_end(self._path)
        transactions = []
        for row in reader:
            try:
                transaction = self._create_transaction(row)
            except Exception as ex:
                print("Issue creating a transaction from row: {}".format(row))
                raise ex
            if from_date <= transaction.date <= to_date:
                transactions.append(transaction)
            else:
                print(
                    "Credit card transaction from a different period: {}".format(
                        transaction
                    )
                )

        return Statement(from_date, to_date, "Santander credit card", transactions)

    def _clean_description(self, description: str) -> str:
        return self._normalize(re.sub("PURCHASE - DOMESTIC", "", description))

    def _create_transaction(self, row: OrderedDict) -> Transaction:
        if row["Card no."]:
            card_num = row["Card no."][-4:]
            msg = "unexpected card number: {}".format(card_num)
            assert card_num == self.CARD_NUMBER_LAST_DIGITS, msg

        return Transaction(
            date=self._parse_date(row["Date"], supported_formats=self.DATE_FORMATS),
            description=self._clean_description(row["Description"]),
            amount=-self._parse_decimal(row["Money in"])
            if row["Money in"]
            else self._parse_decimal(row["Money out"]),
            balance=None,
        )
