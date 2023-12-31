import pandas as pd
import streamlit as st

from statement_processor.db import FinDB
from statement_processor.models import Transaction, TextFeature, TextFeatureType

from statement_processor.data_utils import transactions_to_dataframe
from statement_processor.ui_components import optional_date_filtering


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

    transactions = db.get_transactions()
    df = transactions_to_dataframe(transactions)
    df = optional_date_filtering(df)

    with st.expander("View summary stats"):
        st.dataframe(df.describe())

    if st.checkbox("Edit manually?"):
        edited_df = st.data_editor(df)

        diff = df.compare(edited_df)

        if st.button("Commit changes?"):
            _store_changes(df, edited_df)
    else:
        st.dataframe(df)

    features = db.get_text_features()
    dff = pd.DataFrame(features)
    st.dataframe(dff)
