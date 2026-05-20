from PIL import Image
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PIL import ImageOps
import io
import json
from pathlib import Path
from config import AZURE_ENDPOINT, AZURE_KEY, COUNT_FILE, MAX_OCR_COUNT

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
        with open(path, "rb") as f:
            data = f.read()

    else:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            data = img_bytes.getvalue()

    poller = client.begin_analyze_document("prebuilt-receipt", data)
    result = poller.result()

    # データ抽出
    extracted = {}

    for doc in result.documents:
        fields = doc.fields

        extracted = {
            "date": (
                str(fields.get("TransactionDate").value)
                if fields.get("TransactionDate")
                else None
            ),
            "amount": (str(fields.get("Total").value) if fields.get("Total") else None),
            "shop": (
                clean_shop_name(str(fields.get("MerchantName").value))
                if fields.get("MerchantName")
                else None
            ),
        }

    ocr_count += 1
    save_ocr_count(ocr_count)

    print(f"OCR使用数: {ocr_count}")
    return extracted


def clean_shop_name(text: str):
    if not text:
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return max(lines, key=len) if lines else None
