import json
from pathlib import Path
import shutil
import traceback
import uuid
import zipfile
import streamlit as st
from processor import process_all
from excel_exporter import export_to_excel_from_results
from filter_duplicates_and_rename import filter_duplicates_and_rename
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from frontend.frontend_utils import load_upload_widget_html
from supabase_utils import (
    load_uploaded_files_from_supabase,
    cleanup_old_sessions,
    cleanup_supabase_files,
)
from config import (
    MAX_OCR_COUNT,
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
    TEMP_DIR,
    BUCKET_NAME,
)

# 環境変数読み込み
load_dotenv()
supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


# レイアウト調整
# st.set_page_config(layout="wide")
st.markdown(
    """
<style>
.block-container {
    max-width: 900px;
    margin: auto;
    padding-top: 4rem;
    padding-left: 4rem;
}

.custom-title {
    font-size: 2.2rem;
    font-weight: 700;
    margin-left: 17rem;
}
</style>

<div class="custom-title">レ仕訳</div>
""",
    unsafe_allow_html=True,
)

# サイドバー
with st.sidebar:
    # 除外ワード（任意）
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

# セッションが未作成の場合は新たに作成する。
if "upload_session" not in st.session_state:
    st.session_state.upload_session = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

session_id = st.session_state.upload_session

# アップローダー読み込み（streamlitのアップローダーは携帯でファイルをアップロードできない場合があるため自作する。）
try:
    BASE_DIR = Path(__file__).resolve().parent
    js_dir = BASE_DIR / "frontend" / "static"
    js_files = [
        "supabaseClient.js",
        "excelUploader.js",
        "receiptUploader.js",
        "main.js",
    ]
    css_path = js_dir / "uploader.css"

    js = "\n".join(
        (js_dir / file_name).read_text(encoding="utf-8") for file_name in js_files
    )
    css = css_path.read_text(encoding="utf-8")

except Exception as e:
    st.write("cwd =", Path.cwd())
    st.write("__file__ =", __file__)
    st.write("frontend exists =", Path("frontend").exists())
    st.write("src/frontend exists =", Path("src/frontend").exists())
    st.code(traceback.format_exc())
    st.stop()

unique_id = str(uuid.uuid4())
upload_widget_html = load_upload_widget_html(BASE_DIR, session_id, css, js, unique_id)

components.html(upload_widget_html, height=290)


# 既存エクセルファイルをダウンロード
excel_folder = f"{session_id}/excel"
excel_files = supabase.storage.from_(BUCKET_NAME).list(excel_folder)

if excel_files:
    existing_excel = f"{excel_folder}/{excel_files[0]['name']}"
    excel_bytes = supabase.storage.from_(BUCKET_NAME).download(existing_excel)
else:
    excel_bytes = None

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

display_name_map = {}


button = st.button(
    "処理開始",
)

# 実処理
if button:
    try:
        cleanup_old_sessions(supabase)
        receipt_files = supabase.storage.from_(BUCKET_NAME).list(
            f"{session_id}/receipts"
        )
        if not receipt_files:
            st.warning("レシートをアップロードしてください")
            st.session_state.processing = False
            st.stop()

        uploaded_files = load_uploaded_files_from_supabase(supabase, session_id)

        # レシート一時保存用フォルダ
        receipts_dir = TEMP_DIR / session_id / "receipts"

        # フォルダごと削除
        if receipts_dir.exists():
            shutil.rmtree(receipts_dir)

        # 再作成
        receipts_dir.mkdir(parents=True, exist_ok=True)

        receipts_paths = []

        metadata_bytes = supabase.storage.from_(BUCKET_NAME).download(
            f"{session_id}/metadata.json"
        )
        display_name_map = json.loads(metadata_bytes.decode("utf-8"))

        # レシート出力パス
        for file in uploaded_files:
            temp_path = TEMP_DIR / session_id / "receipts" / file.name
            temp_path.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(file.read())

            receipts_paths.append(str(temp_path))

        # OCR & 抽出
        ocr_results, status, count = process_all(receipts_paths)
        st.write(f"今月の使用回数: {count} / {MAX_OCR_COUNT}")

        if status == "over_limit":
            st.error("今月の利用上限を超えるため処理できませんでした。")
            st.session_state.processing = False
            st.stop()
        if status == "error":
            st.error("OCR処理中にエラーが発生しましたため、処理ができませんでした。")
            st.session_state.processing = False
            st.stop()

        # Excel出力パス
        excel_path = TEMP_DIR / session_id / "excel" / "receipts.xlsx"
        excel_path.parent.mkdir(parents=True, exist_ok=True)

        if excel_bytes:
            with open(excel_path, "wb") as f:
                f.write(excel_bytes)

        else:
            # アップロードがない場合、古いExcel削除
            if excel_path.exists():
                excel_path.unlink()

        # 重複チェック＆リネーム
        filtered_ocr_results, duplicates = filter_duplicates_and_rename(
            excel_path, ocr_results
        )

        # Excel出力
        export_to_excel_from_results(filtered_ocr_results, excel_path, session_id)

        st.success("処理完了")
        if duplicates:
            st.warning(
                f"重複により {len(duplicates)}/{len(uploaded_files)} 件スキップしました"
            )

            with st.expander("重複ファイル一覧"):
                for r, reason in duplicates:

                    filename = Path(r["image"]).name

                    storage_key = f"{session_id}/receipts/{filename}"

                    display_name = display_name_map.get(storage_key, filename)

                    st.write(f"- {display_name}（{reason}）")
        # ダウンロード（重要）
        zip_path = TEMP_DIR / session_id / "Receipt2Excel.zip"
        with zipfile.ZipFile(zip_path, "w") as z:

            # Excel
            z.write(excel_path, excel_path.name)
            # レシート
            for r in filtered_ocr_results:
                file_path = r["image"]
                z.write(file_path, Path(file_path).name)

        with open(zip_path, "rb") as f:
            downloaded = st.download_button(
                "Excel・レシートをダウンロード",
                data=f,
                file_name="Receipt2Excel.zip",
            )
    except Exception as e:
        trace = e
        st.error(f"処理に失敗しました：{trace}")
        st.session_state.status = "idle"
        traceback.print_exc()
    finally:
        cleanup_supabase_files(supabase, session_id)
