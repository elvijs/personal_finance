from datetime import datetime

import pytest
from statement_processor.db import FinDB
from statement_processor.transactions import Transaction


def test_db__is_not_smoking(in_memory_uri: str) -> None:
    db = FinDB(in_memory_uri)
    db.initialize()


def test_can_insert_a_transaction(in_memory_uri: str, transaction: Transaction) -> None:
    db = FinDB(in_memory_uri)
    db.initialize()

    db.insert_transaction(transaction)

    assert db.get_transactions() == [transaction]


def test_can_insert_an_account(in_memory_uri: str) -> None:
    db = FinDB(in_memory_uri)
    db.initialize()

    account = ("id", "type")
    db.insert_account(*account)

    assert db.get_accounts() == [account]


@pytest.fixture
def in_memory_uri() -> str:
    return ":memory:"


@pytest.fixture
def transaction() -> Transaction:
    return Transaction(
        date=datetime.now().date(),
        description="blah",
        amount=3.14,
        account_id="my_amazing_bank",
    )
