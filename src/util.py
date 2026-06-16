from datetime import date, datetime
import streamlit as st


def normalize(v):
    if v is None:
        return None

    # 日付（最優先）
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")

    # 数値
    try:
        return int(float(v))
    except:
        # 文字列
        return str(v).strip()


def has_exclude_company_name(text):

    exclude_word = st.session_state.get("exclude_company_name", "")

    normalized_text = text.replace(" ", "").replace("　", "")
    normalized_exclude = exclude_word.replace(" ", "").replace("　", "")

    return normalized_exclude and normalized_exclude in normalized_text
