from PIL import Image
import pytesseract

def run_ocr(image_path: str) -> str:
    print("DEBUG: image_path =", image_path)

    img = Image.open(image_path)
    print("DEBUG: image opened =", img)

    text = pytesseract.image_to_string(img, lang="jpn")
    print("DEBUG: raw OCR text type =", type(text))

    return text



import re

def extract_amount(text: str) -> int | None:
    if not text:
        return None

    # ==========================
    # ① 普通のレシート（円が読めている）
    # ==========================
    normalized_zen = (
        text.replace("，", ",")
            .replace("．", ".")
            .replace(" ", "")
    )

    yen_patterns = [
        r"今回請求額.*?([0-9,\.]+)円",
        r"総請求額.*?([0-9,\.]+)円",
        r"領収金額.*?([0-9,\.]+)円",
        r"合計.*?([0-9,\.]+)円",
    ]

    for pat in yen_patterns:
        m = re.search(pat, normalized_zen)
        if m:
            value = re.sub(r"[^\d]", "", m.group(1))
            if value.isdigit():
                return int(value)

    # ==========================
    # ② 壊れたレシート用（円・¥が壊れている）
    # ==========================
    normalized = text
    normalized = normalized.replace("O", "0")
    normalized = normalized.replace("o", "0")
    normalized = normalized.replace("一", "")
    normalized = normalized.replace("¥", "")
    normalized = normalized.replace("\\", "")
    normalized = normalized.replace(",", "")
    normalized = normalized.replace(" ", "")

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

def extract_date(text: str) -> str | None:
    pass


def extract_shop(text: str) -> str | None:
    pass


def has_warning(date, amount, shop) -> bool:
    pass


def process_receipt(image_path: str) -> dict:
    pass
    
if __name__ == "__main__":

    image_path = "sample_receipt (2).jpg"  # ここを自分の画像パスに

    text = run_ocr(image_path)
    print("=== OCR結果 ===")
    print(text)

    amount = extract_amount(text)
    print("=== 抽出された金額 ===")
    print(amount)

