from PIL import Image
import pytesseract
import re
import fitz  # PyMuPDF
import io


# ====================
# OCR
# ====================

def run_ocr_image(img: Image.Image) -> str:
    """
    PIL Image -> OCR text
    """
    return pytesseract.image_to_string(img, lang="jpn")


# ====================
# Amount Extraction
# ====================

def extract_amount(text: str) -> int | None:
    if not text:
        return None

    # PDF対策：改行を除去して1行扱い
    normalized_zen = (
        text.replace("\n", "")
            .replace("，", ",")
            .replace("．", ".")
            .replace(" ", "")
    )

    # ① 通常パターン（円 / JPY）
    yen_patterns = [
        r"今回請求額.*?([0-9,\.]+)円",
        r"総請求額.*?([0-9,\.]+)円",
        r"領収金額.*?([0-9,\.]+)円",
        r"合計金額.*?([0-9,\.]+)円",
        r"合計.*?([0-9,\.]+)(?:円|JPY)",
    ]

    for pat in yen_patterns:
        m = re.search(pat, normalized_zen)
        if m:
            value = re.sub(r"[^\d]", "", m.group(1))
            if value.isdigit():
                return int(value)

    # ② 壊れたレシート用（円記号崩壊）
    normalized = (
        text.replace("O", "0")
            .replace("o", "0")
            .replace("一", "")
            .replace("¥", "")
            .replace("\\", "")
            .replace(",", "")
            .replace(" ", "")
    )

    lines = normalized.splitlines()
    candidates = []

    for line in lines:
        if any(key in line for key in ["領収", "金額", "合計", "標準対象"]):
            nums = re.findall(r"[0-9]{3,}", line)
            for n in nums:
                candidates.append(int(n))

    if candidates:
        return max(candidates)

    return None


# ====================
# 未実装（今後）
# ====================

def extract_date(text: str) -> str | None:
    """OCRテキストから日付を抽出（未実装）"""
    pass


def extract_shop(text: str) -> str | None:
    """OCRテキストから店舗名を抽出（未実装）"""
    pass


def has_warning(date, amount, shop) -> bool:
    """不足項目があるか判定（未実装）"""
    pass


def process_receipt(image_path: str) -> dict:
    """画像レシート処理の統合関数（未実装）"""
    pass


# ====================
# PDF Handling
# ====================

def pdf_to_images(pdf_path: str) -> list[Image.Image]:
    doc = fitz.open(pdf_path)
    images = []

    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)

    return images


def extract_amount_from_pdf(pdf_path: str) -> int | None:
    images = pdf_to_images(pdf_path)
    amounts = []

    for img in images:
        text = run_ocr_image(img)
        amount = extract_amount(text)
        if amount is not None:
            amounts.append(amount)

    return max(amounts) if amounts else None


# ====================
# Entry Point
# ====================

if __name__ == "__main__":
    pdf_path = "sample_multi_page_receipt.pdf"
    amount = extract_amount_from_pdf(pdf_path)
    print("PDF全体の金額:", amount)