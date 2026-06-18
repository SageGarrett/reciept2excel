from pathlib import Path
import shutil
import traceback
import uuid
import zipfile
import streamlit as st
from config import (
    EXCEL_DIR,
    MAX_OCR_COUNT,
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
    SUPABASE_PUBLISHABLE_KEY,
    TEMP_DIR,
)
from processor import process_all
from excel_exporter import export_to_excel_from_results
from filter_duplicates_and_rename import filter_duplicates_and_rename
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
from io import BytesIO
import streamlit.components.v1 as components


class SupabaseUploadedFile(BytesIO):
    def __init__(self, file_bytes: bytes, name: str, file_type: str = ""):
        super().__init__(file_bytes)
        self.name = name
        self.type = file_type
        self.size = len(file_bytes)


def load_uploaded_files_from_supabase(supabase, session_id):
    uploaded_files = []

    files = supabase.storage.from_("receipt_files").list(f"uploads/{session_id}")

    for file in files:
        path = f"uploads/{session_id}/{file['name']}"

        file_bytes = supabase.storage.from_("receipt_files").download(path)

        ext = file["name"].split(".")[-1].lower()

        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "pdf": "application/pdf",
            "heic": "image/heic",
            "heif": "image/heif",
        }

        uploaded_files.append(
            SupabaseUploadedFile(
                file_bytes=file_bytes,
                name=file["name"],
                file_type=mime_map.get(ext, ""),
            )
        )

    return uploaded_files


load_dotenv()

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

st.title("Receipt2Excel")


if "upload_session" not in st.session_state:
    st.session_state.upload_session = str(uuid.uuid4())

session_id = st.session_state.upload_session
try:
    js = Path("frontend/uploader.js").read_text(encoding="utf-8")
except Exception as e:
    st.write("cwd =", Path.cwd())
    st.write("__file__ =", __file__)
    st.write("frontend exists =", Path("frontend").exists())
    st.write("src/frontend exists =", Path("src/frontend").exists())
    st.code(traceback.format_exc())
    st.stop()

# # 既存Excelをアップロード（任意）
# existing_excel = st.file_uploader("既存Excelをアップロード（任意）", type="xlsx")
# # レシートをアップロード（複数可）
# uploaded_files = st.file_uploader(
#     "レシートをアップロード（複数可）",
#     type=["jpg", "jpeg", "png", "pdf", "heic", "heif"],
#     accept_multiple_files=True,
# )
existing_excel = None
components.html(
    f"""
    <div>
        <h4>レシートをアップロード（複数可）</h4>

        <input
            type="file"
            id="fileInput"
            multiple
            accept=".jpg,.jpeg,.png,.pdf,.heic,.heif"
        />

        <button onclick="uploadFiles()">
            アップロード
        </button>

        <p id="status"></p>
    </div>

    <script>
        const SUPABASE_URL = "{SUPABASE_URL}";
        const SUPABASE_PUBLISHABLE_KEY = "{SUPABASE_PUBLISHABLE_KEY}";
        const sessionId = "{session_id}";
        {js}
    </script>
    """,
    height=250,
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


if st.button("処理開始"):
    uploaded_files = load_uploaded_files_from_supabase(supabase, session_id)
    files = supabase.storage.from_("receipt_files").list(f"uploads/{session_id}")

    if not files:
        st.warning("先にレシートをアップロードしてください")
        st.stop()

    uploaded_files = load_uploaded_files_from_supabase(supabase, session_id)

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
