from datetime import datetime, date

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta
from statement_processor.db import FinDB


def optional_date_filtering(df_: pd.DataFrame) -> pd.DataFrame:
    if st.checkbox("Filter?"):
        now = datetime.now()
        a_month_ago = now - relativedelta(months=1)
        start_of_last_month = date(a_month_ago.year, a_month_ago.month, 1)
        start_of_current_month = date(now.year, now.month, 1)

        start = st.date_input("From", value=start_of_last_month)
        end = st.date_input("To", value=start_of_current_month)

        df_ = df_[start:end]  # type: ignore  # MyPy doesn't understand pandas

    return df_


def optional_short_descriptions(df: pd.DataFrame, db: FinDB) -> pd.DataFrame:
    if st.checkbox("Add latest features?"):
        features = db.get_text_features()

    return df
