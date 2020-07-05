import csv
import datetime
import logging
from typing import Sequence, List

from statement_processor.rules import IgnoredTransactionType, get_ignore_rules
from statement_processor.transactions import ProcessedTransaction, Transaction

logger = logging.getLogger("Statement reader")


class Statement:
    def __init__(
        self,
        from_date: datetime.date,
        to_date: datetime.date,
        account_number: str,
        transactions: Sequence[Transaction],
    ) -> None:
        self._from_date = from_date
        self._to_date = to_date
        self._account_number = account_number
        self._transactions = transactions

    @property
    def from_date(self) -> datetime.date:
        return self._from_date

    @property
    def to_date(self) -> datetime.date:
        return self._to_date

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def transactions(self) -> Sequence[Transaction]:
        return self._transactions

    def __str__(self) -> str:
        return "Statement from {} to {} for account " "{}\n{}".format(
            self.from_date, self.to_date, self.account_number, self.transactions
        )


class SingleStatementReporter:
    IGNORED_FULL_DESCRIPTIONS = get_ignore_rules(IgnoredTransactionType.full)
    IGNORED_PARTIAL_DESCRIPTIONS = get_ignore_rules(IgnoredTransactionType.partial)

    def __init__(self, statement: Statement) -> None:
        self._statement = statement

    def get_report(self) -> Sequence[ProcessedTransaction]:
        ret = []
        for transaction in self._statement.transactions:
            if self._should_ignore(transaction):
                logger.warn("Ignoring {}".format(transaction))
                continue

            ret.append(
                ProcessedTransaction(
                    transaction.date,
                    transaction.description,
                    transaction.amount,
                    transaction.balance,
                    transaction.bank_category,
                )
            )
        return ret

    def _should_ignore(self, transaction: Transaction) -> bool:
        if transaction.description in self.IGNORED_FULL_DESCRIPTIONS:
            return True

        for partial_ignorable in self.IGNORED_PARTIAL_DESCRIPTIONS:
            if partial_ignorable in transaction.description:
                return True

        return False


class StatementReporter:
    def __init__(self, *statements: Statement) -> None:
        self._statements = statements
        self._validate_statements()

    def get_report(self) -> Sequence[ProcessedTransaction]:
        report: List[ProcessedTransaction] = []
        for statement in self._statements:
            reporter = SingleStatementReporter(statement)
            report += reporter.get_report()
        return report

    def store_report_to_csv(self, path: str) -> None:
        processed_transactions = self.get_report()
        if len(processed_transactions) == 0:
            raise Exception("No transactions")

        fieldnames = processed_transactions[0].as_ordered_dict().keys()

        with open(path, "w") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            for transaction in processed_transactions:
                writer.writerow(transaction.as_ordered_dict())

    def _validate_statements(self):
        if not self._statements:
            return

        from_date = self._statements[0].from_date
        to_date = self._statements[0].to_date

        for statement in self._statements[1:-1]:
            s_msg = "Expected statement start: {}, got: {}".format(
                from_date, statement.from_date
            )
            assert from_date == statement.from_date, s_msg
            e_msg = "Expected statement end: {}, got: {}".format(
                from_date, statement.from_date
            )
            assert to_date == statement.to_date, e_msg
