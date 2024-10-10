import streamlit as st
from statement_processor.db import FinDB
import plotly.express as px

from statement_processor.data_utils import transactions_to_dataframe
from statement_processor.ui_components import optional_filtering

if __name__ == "__main__":
    db = FinDB()

    st.title("Transaction analyser")

    transactions = db.get_transactions()
    df = transactions_to_dataframe(transactions, cast_to_datetime=True)
    df = optional_filtering(df)

    with st.expander("View summary stats"):
        st.dataframe(df.describe())

    with st.expander("View data"):
        st.text(df.index)

    for account in df["account_id"].unique():
        account_transactions = df[df["account_id"] == account]
        agg = account_transactions[["amount", "description"]].resample("D").sum()
        st.plotly_chart(
            px.line(agg, y="amount", text="description", title=account, markers=True)
        )

    agg = df[["amount", "account_id"]].groupby("account_id").sum()
    st.dataframe(agg)
