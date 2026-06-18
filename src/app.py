from pathlib import Path
import shutil
import zipfile
import streamlit as st
from config import EXCEL_DIR, MAX_OCR_COUNT, SUPABASE_KEY, SUPABASE_URL, TEMP_DIR
from processor import process_all
from excel_exporter import export_to_excel_from_results
from filter_duplicates_and_rename import filter_duplicates_and_rename
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Receipt2Excel")

# 既存Excelをアップロード（任意）
existing_excel = st.file_uploader("既存Excelをアップロード（任意）", type="xlsx")
# レシートをアップロード（複数可）
uploaded_files = st.file_uploader(
    "レシートをアップロード（複数可）",
    type=["jpg", "jpeg", "png", "pdf", "heic", "heif"],
    accept_multiple_files=True,
)


# 除外ワード（任意）
with st.sidebar:
    with st.container(border=True):
        st.markdown(
            """
            **会社名**  
            <span style='font-size:0.8em;color:gray'>※支払先の出力の対象外にする</span>
            """,
            unsafe_allow_html=True,
        )

        exclude_company_name = st.text_input(
            label="会社名",
            label_visibility="collapsed",
            key="exclude_company_name",
        )

    # 決算期入力
    # with st.sidebar:
    with st.container(border=True):
        st.markdown(
            """
            **決算期**  
            <span style='font-size:0.8em;color:gray'>※終了年月を入力</span>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([3, 2])

        now = datetime.now()

        # デフォルト決算月
        default_fiscal_month = 3

        # 3月決算で、4月以降なら翌年
        if now.month > default_fiscal_month:
            default_fiscal_year = now.year + 1
        else:
            default_fiscal_year = now.year

        with col1:
            fiscal_year = st.number_input(
                "年度",
                min_value=2020,
                max_value=2100,
                value=default_fiscal_year,
                step=1,
                key="fiscal_year",
            )

        with col2:
            fiscal_month = st.selectbox("月", range(1, 13), index=2, key="fiscal_month")

        # 表示用の対象期間計算
        if fiscal_month == 12:
            start = datetime(fiscal_year, 1, 1)
            end = datetime(fiscal_year + 1, 1, 1)
        else:
            start = datetime(fiscal_year - 1, fiscal_month + 1, 1)
            end = datetime(fiscal_year, fiscal_month + 1, 1)
        st.caption(f"決済期: {start:%Y/%m/%d} ～ {(end - timedelta(days=1)):%Y/%m/%d}")


if uploaded_files:

    st.write(f"{len(uploaded_files)}ファイル選択")

    if st.button("処理開始"):

        # レシート一時保存用フォルダ
        receipts_dir = TEMP_DIR / "receipts"

        # フォルダごと削除
        if receipts_dir.exists():
            shutil.rmtree(receipts_dir)

        # 再作成
        receipts_dir.mkdir(parents=True, exist_ok=True)

        receipts_paths = []

        # レシート出力パス
        for file in uploaded_files:
            temp_path = TEMP_DIR / "receipts" / file.name
            temp_path.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(file.read())

            receipts_paths.append(str(temp_path))

        # OCR & 抽出
        ocr_results, status, count = process_all(receipts_paths)
        st.write(f"今月の使用回数: {count} / {MAX_OCR_COUNT}")

        if status == "over_limit":
            st.error("今月の利用上限を超えるため処理できませんでした。")
            st.stop()
        if status == "error":
            st.error("OCR処理中にエラーが発生しましたため、処理ができませんでした。")
            st.stop()

        # Excel出力パス
        excel_path = EXCEL_DIR
        excel_path.parent.mkdir(parents=True, exist_ok=True)

        if existing_excel:
            with open(excel_path, "wb") as f:
                f.write(existing_excel.read())

        else:
            # アップロードがない場合、古いExcel削除
            if excel_path.exists():
                excel_path.unlink()

        # 重複チェック＆リネーム
        filtered_ocr_results, duplicates = filter_duplicates_and_rename(
            excel_path, ocr_results
        )

        # Excel出力
        export_to_excel_from_results(filtered_ocr_results, excel_path)

        st.success("処理完了")

        if duplicates:
            st.warning(
                f"重複により {len(duplicates)}/{len(uploaded_files)} 件スキップしました"
            )

            with st.expander("重複ファイル一覧"):
                for r, reason in duplicates:
                    filename = Path(r["image"]).name
                    st.write(f"- {filename}（{reason}）")

        # ダウンロード（重要）
        zip_path = TEMP_DIR / "Receipt2Excel.zip"
        with zipfile.ZipFile(zip_path, "w") as z:

            # Excel
            z.write(excel_path, excel_path.name)
            # レシート
            for r in filtered_ocr_results:
                file_path = r["image"]
                z.write(file_path, Path(file_path).name)

        with open(zip_path, "rb") as f:
            st.download_button(
                "Excel・レシートをダウンロード",
                data=f,
                file_name="Receipt2Excel.zip",
            )
