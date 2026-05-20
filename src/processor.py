from datetime import datetime, date
from PIL import Image
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PIL import ImageOps
import io
import json
from pathlib import Path
from pdf2image import convert_from_path
from config import AZURE_ENDPOINT, AZURE_KEY, COUNT_FILE, MAX_OCR_COUNT
from extractors import extract_amount, extract_date, extract_shop
from util import normalize

# ====================
# client
# ====================
client = DocumentAnalysisClient(
    endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
)


# ====================
# count管理
# ====================
def load_ocr_count():
    if Path(COUNT_FILE).exists():
        with open(COUNT_FILE, "r") as f:
            return json.load(f).get("count", 0)
    return 0


def save_ocr_count(count):
    with open(COUNT_FILE, "w") as f:
        json.dump({"count": count}, f)


# 初期化
ocr_count = load_ocr_count()


def process_all(files: list[str], progress_callback=None) -> list[dict]:
    results = []
    total = len(files)

    for i, path in enumerate(files):

        result = run_ocr_receipt_azure(path)

        results.append(result)

        if progress_callback:
            progress_callback(i + 1, total)

    return results


def run_ocr_receipt_azure(path: str):

    global ocr_count

    if ocr_count >= MAX_OCR_COUNT:
        print("OCR上限に到達しました（停止）")
        return None

    if path.lower().endswith(".pdf"):
        images = convert_from_path(path)

    else:
        # 画像の場合
        images = [Image.open(path)]

    results = []
    full_text_list = []

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
        result = poller.result()

        # 全テキストを取得する（後続の補完ロジック用）
        page_text = "\n".join(
            line.content for page in result.pages for line in page.lines
        )
        full_text_list.append(page_text)

        for doc in result.documents:
            fields = doc.fields

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

            results.append(extracted)

        ocr_count += 1
        save_ocr_count(ocr_count)
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

    print(f"OCR使用数: {ocr_count}")

    return {"image": path, **merged}


def clean_shop_name(text: str):
    if not text:
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return max(lines, key=len) if lines else None


def merge_results(results):

    if not results:
        return {"date": None, "amount": None, "shop": None}

    date = next((r["date"] for r in results if r["date"]), None)

    amounts = [r["amount"] for r in results if r["amount"]]
    amount = max(amounts) if amounts else None

    shop = next((r["shop"] for r in results if r["shop"]), None)

    return {"date": date, "amount": amount, "shop": shop}
