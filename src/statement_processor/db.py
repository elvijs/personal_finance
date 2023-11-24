from datetime import date
from typing import Sequence
from pathlib import Path
import sqlite3

from statement_processor.transactions import Transaction

_DEFAULT_DB = Path(__file__).parent.parent.parent / "data" / "finance.db"
SCHEMA = Path(__file__).parent / "schema.sql"


class FinDB:
    def __init__(self, db_uri: str = str(_DEFAULT_DB)) -> None:
        self._conn = sqlite3.connect(db_uri)

    def initialize(self) -> None:
        cursor = self._conn.cursor()
        schema_sql = SCHEMA.read_text()
        cursor.executescript(schema_sql)
        self._conn.commit()

    def insert_transaction(self, transaction: Transaction) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (date, description, amount, account_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                transaction.date.isoformat(),
                transaction.description,
                transaction.amount,
                transaction.account_id,
            ),
        )
        self._conn.commit()

    def get_transactions(self) -> Sequence[Transaction]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
        return [
            Transaction(date.fromisoformat(date_str), description, amount, account_id)
            for id_, date_str, description, amount, account_id in rows
        ]

    def close(self):
        self._conn.close()


# Example usage:
if __name__ == "__main__":
    db = FinDB()

    # Insert a transaction
    t = Transaction(date(2023, 11, 24), "Stuff", 50.0, account_id="revolut")
    db.insert_transaction(t)

    # Retrieve transactions
    transactions = db.get_transactions()
    for row in transactions:
        print(row)

    db.close()
