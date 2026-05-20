from filter_duplicates_and_rename import filter_duplicates_and_rename
from config import BASE_DIR, EXCEL_DIR, RECEIPTS_DIR, TEMP_DIR
from excel_exporter import export_to_excel_from_results
from processor import process_all
from rename import rename_files
from pathlib import Path

# file_paths = [
#     "交際費 20250529  沁みる .jpg",
#     "事務用品費_20260320_冷蔵庫 .pdf",
#     "健康診断_sample.jpg",
#     "Bronze_DBA_参考書_領収書.pdf",
#     "交通費_sample.jpg",
# ]
RECEIPTS_DIR = BASE_DIR / "temp" / "test_receipts"
file_paths = [
    "事務用品費_冷蔵庫 重複だけどPDFを画像化.jpg",
    "インターネット_重複だけどJPEGからPNGに変換.png",
    "ライフ_sample_5_重複なし.jpg",
    "健康診断_ただの重複.jpg",
]


def test(file_paths):

    import shutil

    receipts_dir = RECEIPTS_DIR

    # フォルダごと削除
    if receipts_dir.exists():
        shutil.rmtree(receipts_dir)

    # 再作成
    receipts_dir.mkdir(parents=True, exist_ok=True)

    receipts_paths = []

    # レシート出力パス
    for file in file_paths:

        receipt_name = Path(file)
        original_receipts = BASE_DIR / receipt_name
        receipt_path = TEMP_DIR / "test_receipts" / receipt_name
        shutil.copy(original_receipts, receipt_path)

        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipts_paths.append(str(receipt_path))

    # OCR & 抽出
    ocr_results = process_all(receipts_paths)

    # Excel出力パス
    excel_path = Path("receipts.xlsx")
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    # 重複チェック＆リネーム
    filtered_ocr_results, duplicates = filter_duplicates_and_rename(
        excel_path, ocr_results
    )

    # Excel出力
    export_to_excel_from_results(filtered_ocr_results, excel_path)


results = test(file_paths)
