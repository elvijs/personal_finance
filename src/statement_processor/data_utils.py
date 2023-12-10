from typing import Sequence

import pandas as pd
from statement_processor.models import Transaction


def to_dataframe(
    transactions: Sequence[Transaction],
    cast_to_datetime: bool = False,
    drop_balance_statements: bool = True,
) -> pd.DataFrame:
    if drop_balance_statements:
        transactions = [
            t for t in transactions if "INITIAL BALANCE" not in t.description
        ]

    as_df = pd.DataFrame(data=transactions)
    if cast_to_datetime:
        as_df["date"] = pd.to_datetime(as_df["date"])
    else:
        as_df["date"] = pd.to_datetime(as_df["date"]).dt.date

    as_df.set_index("date", inplace=True)
    as_df.sort_index(inplace=True)

    return as_df
