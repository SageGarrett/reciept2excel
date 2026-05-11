import pytesseract
from PIL import Image
import re

# 画像読み込み
img = Image.open("sample_receipt.jpg")

# 拡大だけ（安全）
img = img.resize(
    (img.width * 2, img.height * 2),
    Image.BICUBIC
)

# OCR（シンプル設定）
text = pytesseract.image_to_string(
    img,
    lang="jpn",
    config="--psm 3"
)

print("=== OCR RAW ===")
print(repr(text))
print("===============\n")

# よくある誤認識を補正
normalized = text.replace("Y", "¥").replace("B", "8")

# 金額っぽいものを探す
patterns = [
    r'¥\s*([0-9,]+)',      # ¥1,234
    r'金額\s*([0-9,]+)',  # 金額 1234
    r'合計\s*([0-9,]+)',  # 合計 1234
    r'([0-9,]{3,})円'     # 1234円
]

amount = None
for p in patterns:
    m = re.search(p, normalized)
    if m:
        amount = m.group(1).replace(",", "")
        break

print("=== AMOUNT ===")
print(amount)