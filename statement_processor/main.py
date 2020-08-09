"""
A few simple scripts to manipulate bank and credit card statements
into a uniform format.
"""
import datetime
import getpass
import glob
import logging
from typing import Sequence

from dateutil.relativedelta import relativedelta

from statement_processor.readers import (RevolutStatementReader,
                                         SantanderBankStatementReader,
                                         SantanderCreditCardStatementReader)
from statement_processor.statements import StatementReporter

logger = logging.getLogger("Statement processing")

user = getpass.getuser()
THIS_MONTHS_PATH = "/home/{}/Documents/finances/".format(user) + "{year}/{month}/"


def get_santander_bank_account_paths(at_path: str) -> Sequence[str]:
    return glob.glob(at_path + "Statements*.txt")


def get_santander_credit_card_statement_paths(at_path: str) -> Sequence[str]:
    return glob.glob(at_path + "Report*.txt")


def get_revolut_statement_path(at_path: str) -> str:
    all_matches = glob.glob(at_path + "Revolut*")
    assert len(all_matches) == 1, \
        f"Expected to find precisely one Revolut statement, " \
        f"instead got {len(all_matches)}: {all_matches}"
    return all_matches[0]


def get_last_months_year() -> str:
    last_month = datetime.datetime.now() - relativedelta(months=1)
    return last_month.strftime("%Y")


def get_last_month_name() -> str:
    last_month = datetime.datetime.now() - relativedelta(months=1)
    return last_month.strftime("%B")


def get_last_months_dir() -> str:
    return THIS_MONTHS_PATH.format(
        year=get_last_months_year(), month=get_last_month_name()
    )


if __name__ == "__main__":
    last_months_dir = get_last_months_dir()

    statements = [
        SantanderBankStatementReader(path).get_statement()
        for path in get_santander_bank_account_paths(last_months_dir)
    ]

    statements += [
        SantanderCreditCardStatementReader(path).get_statement()
        for path in get_santander_credit_card_statement_paths(last_months_dir)
    ]

    try:
        revolut_path = get_revolut_statement_path(last_months_dir)
    except IndexError:
        raise IndexError(
            "No Revolut statement found, please upload to " "{}".format(last_months_dir)
        )
    revolut_statement = RevolutStatementReader(revolut_path).get_statement()
    statements.append(revolut_statement)

    report_path = last_months_dir + "report.csv"
    StatementReporter(*statements).store_report_to_csv(report_path)
