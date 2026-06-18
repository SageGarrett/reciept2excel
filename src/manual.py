import streamlit as st

st.set_page_config(page_title="マニュアル", layout="wide")

with st.sidebar:
    st.title("目次")
    st.markdown("""
    - [1. 基本的な使い方](#basic)
    - [2. オプション設定](#options)
    - [3. FAQ](#faq)
    - [4. 注意事項](#notes)
    """)
