from datetime import datetime
import streamlit as st
from PIL import Image, ImageOps
import io
from pdf2image import convert_from_path
from config import AZURE_ENDPOINT, AZURE_KEY, client, supabase, MAX_OCR_COUNT
from extractors import extract_amount, extract_date, extract_shop
from util import normalize
import traceback
import pillow_heif

# HEIF保存サポートを有効化
pillow_heif.register_heif_opener()


def process_all(files: list[str]) -> list[dict]:

    st.write("ENDPOINT:", AZURE_ENDPOINT)
    st.write("KEY:", AZURE_KEY)

    results = []

    # OCR使用回数管理テーブル取得（使用回数、年月）
    load_ocr_usage = load_ocr_count()

    # 月が変わってたらテーブル使用回数を0とする
    table_month = load_ocr_usage["month"]
    current_month = datetime.now().strftime("%Y-%m")

    if month_is_changed(table_month, current_month):
        table_ocr_count = 0
    else:
        table_ocr_count = load_ocr_usage["count"]

    # ファイルごとに画像を読み込む（PDFはページごとに分割）
    file_images_map = {}

    for path in files:
        if path.lower().endswith(".pdf"):
            # PDF内のページをJPEGに変換
            file_images_map[path] = convert_from_path(path)

        elif path.lower().endswith((".heif", ".heic")):
            # HEIC → JPEG変換
            img = Image.open(path)

            buffer = io.BytesIO()
            img.convert("RGB").save(buffer, format="JPEG")
            buffer.seek(0)

            # OCRに渡しやすい形に（PILに戻す）
            file_images_map[path] = [Image.open(buffer)]

        else:
            file_images_map[path] = [Image.open(path)]

    # 読込データのOCR回数を見積もる
    expected_ocr_count = sum(len(images) for images in file_images_map.values())

    status = "ok"

    if table_ocr_count + expected_ocr_count > MAX_OCR_COUNT:
        status = "over_limit"
        return [], status, table_ocr_count

    # 処理件数データカウンター
    actual_ocr_count = 0
    # 読込データ数分
    try:
        for path, images in file_images_map.items():
            try:  # OCR解析＆抽出を実行する。
                result_text, result_count = run_ocr_receipt_azure(images)
                actual_ocr_count += result_count

                if result_text:
                    # 抽出したファイルパス、支払い日、支払い金額、支払い先を設定
                    result = {"image": path, **result_text}
                    results.append(result)

            except Exception as e:
                print(f"OCR失敗: {path}: {e}")
                traceback.print_exc()
                status = "error"

    finally:

        actual_total_count = table_ocr_count + actual_ocr_count
        save_ocr_count(actual_total_count, current_month)

    return results, status, actual_total_count


def run_ocr_receipt_azure(images: list[Image.Image]) -> dict:

    results = []
    full_text_list = []
    processed_pages = 0

    for img in images:

        img = ImageOps.exif_transpose(img)
        # サイズ圧縮
        img.thumbnail((2000, 2000))

        if img.mode == "RGBA":
            img = img.convert("RGB")

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)

        data = img_bytes.getvalue()

        poller = client.begin_analyze_document("prebuilt-receipt", data)
        processed_pages += 1
        print(f"processed_pages:{processed_pages}")
        result = poller.result()

        # 全テキストを取得する（後続の補完ロジック用）
        page_text = "\n".join(
            line.content for page in result.pages for line in page.lines
        )
        full_text_list.append(page_text)

        for doc in result.documents:
            fields = doc.fields
            st.write("抽出フィールド:", fields.keys())
            extracted = {
                "date": normalize(
                    (fields.get("TransactionDate").value)
                    if fields.get("TransactionDate")
                    else None
                ),
                "amount": normalize(
                    (fields.get("Total").value) if fields.get("Total") else None
                ),
                "shop": (
                    clean_shop_name(fields.get("MerchantName").value)
                    if fields.get("MerchantName")
                    else None
                ),
            }
            st.write("抽出結果:", extracted)
            results.append(extracted)

        img.close()

    merged = merge_results(results)

    # 全テキストのリストを一行にまとめる
    full_text = "\n".join(full_text_list)

    # 補完ロジック
    if not merged["date"]:
        merged["date"] = extract_date(full_text)

    if not merged["amount"]:
        merged["amount"] = extract_amount(full_text)

    if not merged["shop"] or merged["shop"] == "株式会社SUN":
        merged["shop"] = extract_shop(full_text)

    return merged, processed_pages


def load_ocr_count():
    data = supabase.table("usage").select("*").execute()

    if not data.data:
        return {"count": 0, "month": None}

    return data.data[0]


def month_is_changed(table_month, current_month):
    if table_month != current_month:
        return True

    return False


def save_ocr_count(count, month):
    supabase.table("usage").upsert({"id": 1, "count": count, "month": month}).execute()


def convert_heif_to_jpeg(uploaded_file):

    pillow_heif.register_heif_opener()

    image = Image.open(uploaded_file)

    # JPEGに変換
    buffer = io.BytesIO()
    image.convert("RGB")


def clean_shop_name(text: str):
    if not text:
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return max(lines, key=len) if lines else None


def merge_results(results):
    # 複数ページの結果をマージするロジック。日付と店名は最初に見つかったもの、金額は最大値を採用する。
    if not results:
        return {"date": None, "amount": None, "shop": None}

    date = next((r["date"] for r in results if r["date"]), None)

    amounts = [r["amount"] for r in results if r["amount"]]
    amount = max(amounts) if amounts else None

    shop = next((r["shop"] for r in results if r["shop"]), None)

    return {"date": date, "amount": amount, "shop": shop}
