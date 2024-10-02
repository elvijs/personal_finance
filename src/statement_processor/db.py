import logging
from datetime import date, datetime
from typing import Sequence, Tuple, Optional
from pathlib import Path
import sqlite3

from dateutil.parser import isoparse
from statement_processor.models import Transaction, TextFeature

_DEFAULT_DB = Path(__file__).parent.parent.parent / "data" / "finance.db"
SCHEMA = Path(__file__).parent / "schema.sql"
LOG = logging.getLogger(__file__)


class FinDB:
    def __init__(self, db_uri: str = str(_DEFAULT_DB)) -> None:
        self._conn = sqlite3.connect(db_uri)

    def initialize(self) -> None:
        cursor = self._conn.cursor()
        schema_sql = SCHEMA.read_text()
        cursor.executescript(schema_sql)
        self._conn.commit()

    def insert_transaction(
        self, t: Transaction, ignore_duplicates: bool = False
    ) -> None:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
            INSERT INTO transactions (date, description, amount, account_id, is_shared_expense)
            VALUES (?, ?, ?, ?, ?)
            """,
                (
                    t.date.isoformat(),
                    t.description,
                    t.amount,
                    t.account_id,
                    int(t.is_shared_expense),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as err:
            if ignore_duplicates:
                LOG.debug(f"Transaction already in DB: {t}, skipping")
            else:
                raise err

    def update_transaction(
        self,
        t: Transaction,
        account_id: Optional[str] = None,
        is_shared_expense: Optional[bool] = None,
    ) -> None:
        """Update an existing transaction. Note that only fields that don't form the primary key can be updated."""
        cursor = self._conn.cursor()

        if account_id is None and is_shared_expense is None:
            # no new data provided
            return

        account_id = account_id or t.account_id
        is_shared_expense = (
            is_shared_expense if is_shared_expense is not None else t.is_shared_expense
        )

        cursor.execute(
            """
            UPDATE transactions
            SET account_id = ?, is_shared_expense = ?, updated_on = ?
            WHERE date = ? AND description = ? AND amount = ?
            """,
            (
                account_id,
                int(is_shared_expense),
                datetime.now().isoformat(),
                t.date.isoformat(),
                t.description,
                t.amount,
            ),
        )
        self._conn.commit()

    def get_transactions(self) -> Sequence[Transaction]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
        return [
            Transaction(
                date.fromisoformat(date_str),
                description,
                amount,
                account_id,
                bool(is_shared_expense),
                isoparse(inserted_on),
                isoparse(updated_on),
            )
            for date_str, description, amount, account_id, is_shared_expense, inserted_on, updated_on in rows
        ]

    def insert_text_feature(self, feature: TextFeature) -> None:
        cursor = self._conn.cursor()
        d, desc, amount = feature.transaction_id
        cursor.execute(
            """
            INSERT INTO text_features (name, value, origin, t_date, t_description, t_amount)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                feature.name,
                feature.value,
                feature.origin,
                d.isoformat(),
                desc,
                amount,
            ),
        )
        self._conn.commit()

    def get_text_features(self) -> Sequence[TextFeature]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM text_features")
        rows = cursor.fetchall()
        return [
            TextFeature(
                name=name,
                transaction_id=(isoparse(t_date), t_desc, t_amount),
                value=value,
                origin=origin,
            )
            for name, value, origin, _, t_date, t_desc, t_amount in rows
        ]

    def insert_account(self, id_: str, type_: str) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (id, account_type)
            VALUES (?, ?)
            """,
            (id_, type_),
        )
        self._conn.commit()

    def get_accounts(self) -> Sequence[Tuple[str, str, str]]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        rows = cursor.fetchall()
        return rows

    def close(self):
        self._conn.close()


# Example usage:
if __name__ == "__main__":
    db = FinDB()

    # Insert a transaction
    transaction = Transaction(date(2023, 11, 24), "Stuff", 50.0, account_id="revolut")
    db.insert_transaction(transaction)

    # Retrieve transactions
    transactions = db.get_transactions()
    for row in transactions:
        print(row)

    db.close()
