import streamlit as st
from file_utils import load_image_from_upload

st.title("Receipt2Excel")
st.write("PDF → 画像変換（環境確認）✅")

uploaded_files = st.file_uploader(
    "レシートをアップロード（JPEG / PNG / PDF）",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    for f in uploaded_files:
        st.subheader(f.name)
        image = load_image_from_upload(f)
        st.image(image, width=700)