import argparse
import dataclasses
import logging
from pathlib import Path
from typing import Optional

from statement_processor.db import FinDB
from statement_processor.readers import (
    SantanderBankStatementReader,
    SantanderCreditCardStatementReader,
    RevolutStatementReader,
    StatementReader,
)

LOG = logging.getLogger(__file__)


@dataclasses.dataclass(frozen=True)
class Args:
    finances_dir: Path
    only_last_month: bool


def _get_cli_args() -> Args:
    parser = argparse.ArgumentParser(description="A simple CLI parser example")
    parser.add_argument(
        "-f",
        "--finances_dir",
        help="Path to the finances dir containing raw statements",
        type=str,
    )
    parser.add_argument(
        "-l",
        "--only_last_month",
        help="Should we only import last month's transactions?",
        action="store_true",
    )

    args_ = parser.parse_args()
    parsed_args = Args(
        finances_dir=Path(args_.finances_dir), only_last_month=args_.only_last_month
    )
    return parsed_args


def get_reader(path: Path) -> Optional[StatementReader]:
    if path.suffix == ".txt":
        if path.stem.startswith("Statements"):
            return SantanderBankStatementReader(path)
        elif path.stem.startswith("Report"):
            return SantanderCreditCardStatementReader(path)
        else:
            raise ValueError(f"Could not match the statement '{path}' to a reader")
    elif path.suffix == ".csv":
        if path.stem.lower().startswith("revolut"):
            return RevolutStatementReader(path)
        else:
            LOG.debug(f"Skipping {path}, does not look like a statement")
            return None
    elif path.name.startswith("."):
        LOG.debug(f"Skipping {path}, does not look like a statement")
        return None
    elif path.suffix == ".ods":
        LOG.debug(f"Skipping {path}, does not look like a statement")
        return None
    else:
        raise ValueError(f"Unrecognised file: {path}")


def main(finances_dir: Path) -> None:
    db = FinDB()
    db.initialize()

    for path in finances_dir.rglob("*"):
        if path.is_dir():
            continue

        reader = get_reader(path)
        if reader:
            statement = reader.get_statement()
            transactions = statement.transactions
            if not transactions:
                LOG.info(f"No transactions for {path}")
                continue

            for t in transactions:
                # the same transaction can be represented in more than 1
                db.insert_transaction(t, ignore_duplicates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = _get_cli_args()
    main(args.finances_dir)
