from pathlib import Path
import streamlit as st
from processor import process_all
from excel_exporter import export_to_excel_from_results
from rename import rename_files
from filter_duplicates_and_rename import filter_duplicates_and_rename
import zipfile
from config import EXCEL_DIR, TEMP_DIR

st.title("Receipt2Excel")

# 既存Excelをアップロード（任意）
existing_excel = st.file_uploader("既存Excelをアップロード（任意）", type="xlsx")
# レシートをアップロード（複数可）
uploaded_files = st.file_uploader(
    "レシートをアップロード（複数可）",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
)

if uploaded_files:

    st.write(f"{len(uploaded_files)}ファイル選択")

    if st.button("処理開始"):

        import shutil

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
        ocr_results = process_all(receipts_paths)

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
