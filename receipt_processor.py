def run_ocr(image_path: str) -> str:
    pass


import re

def extract_amount(text: str) -> int | None:
    """
    OCRテキストから金額（円）を抽出して int で返す
    取れなければ None
    """

    if not text:
        return None

    # ---- 最低限の正規化（壊しすぎない）----
    normalized = text
    normalized = normalized.replace("O", "0")
    normalized = normalized.replace("o", "0")
    normalized = normalized.replace("．", ".")
    normalized = normalized.replace(",", ",")
    normalized = normalized.replace(" ", "")

    # ---- ① キーワード優先 ----
    keyword_patterns = [
        r"今回請求額.*?([0-9,\.]+)円",
        r"総請求額.*?([0-9,\.]+)円",
        r"合計.*?([0-9,\.]+)円",
        r"領収額.*?([0-9,\.]+)円",
    ]

    for pat in keyword_patterns:
        m = re.search(pat, normalized)
        if m:
            value = re.sub(r"[^\d]", "", m.group(1))
            if value.isdigit():
                return int(value)

    # ---- ② 円表記を総当たり ----
    candidates = []
    for m in re.findall(r"([0-9][0-9,\.]{2,})円", normalized):
        value = re.sub(r"[^\d]", "", m)
        if value.isdigit():
            candidates.append(int(value))

    if candidates:
        print("DEBUG candidates:", candidates)
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
    sample_text = """
    今回請求額 3,300 円
    総請求額 3.300 円
    """

    amount = extract_amount(sample_text)
    print("抽出された金額:", amount)
