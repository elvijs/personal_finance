from datetime import datetime, date

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from statement_processor.db import FinDB
from statement_processor.models import Transaction, TextFeature, TextFeatureType


def _load_transactions(fin_db: FinDB) -> pd.DataFrame:
    transactions = fin_db.get_transactions()

    as_df = pd.DataFrame(data=transactions)
    as_df["date"] = pd.to_datetime(as_df["date"]).dt.date
    as_df.set_index("date", inplace=True)
    as_df.sort_index(inplace=True)

    return as_df


def _optional_date_filtering(df_: pd.DataFrame) -> pd.DataFrame:
    if st.checkbox("Filter?"):
        now = datetime.now()
        a_month_ago = now - relativedelta(months=1)
        start_of_last_month = date(a_month_ago.year, a_month_ago.month, 1)
        start_of_current_month = date(now.year, now.month, 1)

        start = st.date_input("From", value=start_of_last_month)
        end = st.date_input("To", value=start_of_current_month)

        df_ = df_[start:end]  # type: ignore  # MyPy doesn't understand pandas

    return df_


def _store_changes(old_df: pd.DataFrame, new_df: pd.DataFrame) -> None:
    for (_, old), (_, new) in zip(
        old_df.reset_index().iterrows(), new_df.reset_index().iterrows()
    ):
        if old["is_shared_expense"] != new["is_shared_expense"]:
            # make sure we don't accidentally overwrite any other fields
            t = Transaction(**{k: old[k] for k in old.index})
            db.update_transaction(t, is_shared_expense=new["is_shared_expense"])
            st.text(f"Updated transaction: {t}")

        if old["description"] != new["description"]:
            f = TextFeature(
                name=TextFeatureType.SHORT_DESCRIPTION,
                transaction_id=(
                    old["date"],
                    old["description"],
                    old["amount"],
                ),
                value=new["description"],
                origin="manual",
            )
            db.insert_text_feature(f)
            st.text(f"Inserted feature: {f}")


if __name__ == "__main__":
    db = FinDB()

    st.title("Transaction viewer")

    df = _load_transactions(db)
    df = _optional_date_filtering(df)

    with st.expander("View summary stats"):
        st.dataframe(df.describe())

    if st.checkbox("Edit manually?"):
        edited_df = st.data_editor(df)

        diff = df.compare(edited_df)

        if st.button("Commit changes?"):
            _store_changes(df, edited_df)
    else:
        st.dataframe(df)
