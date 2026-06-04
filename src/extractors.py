from datetime import datetime
import re
from config import (
    AMOUNT_PRIORITY_KEYWORDS,
    CURRENCY_SYMBOLS,
    DATE_KEYWORDS,
    IGNORE_WORDS,
)


def extract_amount(text: str) -> int | None:
    if not text:
        return None

    lines = text.splitlines()

    lines = [
        l.replace(",", "").replace(" ", "").replace("　", "")
        for l in lines
        if l.strip()
    ]

    # 合計キーワード（最優先）
    for i, line in enumerate(lines):

        if any(k in line for k in AMOUNT_PRIORITY_KEYWORDS):
            if i + 1 < len(lines):
                for j in range(i + 1, min(i + 4, len(lines))):
                    target_line = lines[j]
                    nums = re.findall(r"\d+", target_line)

                    if nums:
                        return int(nums[-1])

    # 但の前に金額があるパターン
    for i, line in enumerate(lines):
        if "但" in line:
            for j in range(i - 1, max(i - 4, -1), -1):
                target_line = lines[j]
                nums = re.findall(r"\d+", target_line)

                if nums:
                    return int(nums[-1])

    # ¥ベース(最大値取得)
    candidates = []

    for line in lines:
        if any(sym in line for sym in CURRENCY_SYMBOLS):
            nums = re.findall(r"\d+", line)

            for n in nums:
                candidates.append(int(n))

    if candidates:
        return max(candidates)

    return None


def extract_date(text: str) -> str | None:
    if not text:
        return None

    lines = [
        l.replace(" ", "").replace("　", "") for l in text.splitlines() if l.strip()
    ]

    # 日付キーワード
    for line in lines:
        if any(keyword in line for keyword in DATE_KEYWORDS):
            m = re.search(r"(20\d{2})[/\-年](\d{1,2})[/\-月](\d{1,2})", line)
            if m:
                y, mth, d = m.groups()
                if month_day_checker(y, mth, d):
                    return f"{y}-{int(mth):02d}-{int(d):02d}"

    # 西暦
    for line in lines:

        m = re.search(r"(20\d{2})[/\-年](\d{1,2})[/\-月](\d{1,2})", line)
        if m:
            y, mth, d = m.groups()
            if month_day_checker(y, mth, d):
                return f"{y}-{int(mth):02d}-{int(d):02d}"

    # 和暦（令和・R）
    for line in lines:
        m = re.search(r"(?:令和|R)(\d{1,2})年(\d{1,2})月(\d{1,2})", line)
        if m:
            y, mth, d = m.groups()
            year = 2018 + int(y)
            if month_day_checker(year, mth, d):
                return f"{year}-{int(mth):02d}-{int(d):02d}"

    return None


def month_day_checker(y, mth, d) -> bool:
    try:
        datetime(int(y), int(mth), int(d))
        return True
    except ValueError:
        return False


def extract_shop(text: str) -> str | None:
    if not text:
        return None

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if not lines:
        return None

    # ノイズっぽい行は除外
    lines = [l for l in lines if not is_noise(l)]

    if not lines:
        return None

    return max(lines, key=score)


def is_noise(text):

    if not text:
        return True

    # 1文字のみ
    if len(text) <= 1:
        return True

    # 数字・記号のみ含む
    if re.fullmatch(r"[\d\s\-\.,:/¥#\+()]+", text):
        return True

    # 除外キーワードを含む
    if any(w in text for w in IGNORE_WORDS):
        return True

    return False


def score(text):

    score = 0

    # 日本語がある
    if re.search(r"[ぁ-んァ-ン一-龥]", text):
        score += 3

    # 英語がある
    if re.search(r"[A-Za-z]", text):
        score += 3

    # 長い（それっぽい）
    score += len(text)

    # 店っぽいキーワード
    if re.search(r"(店|株式会社|会社|医院|クリニック|法人)", text):
        score += 5

    # 数字多すぎ
    digit_ratio = sum(c.isdigit() for c in text) / len(text)
    if digit_ratio > 0.5:
        score -= 5

    return score
