import os
from pathlib import Path
import streamlit as st
from supabase import create_client
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
DEBUG_DIR = TEMP_DIR / "receipts" / "ocr_debug"
BUCKET_NAME = "Uploads"


def get_secret(key):
    try:
        return st.secrets[key]  # Cloud
    except Exception:
        return os.getenv(key)  # Local


AZURE_ENDPOINT = get_secret("AZURE_ENDPOINT")
AZURE_KEY = get_secret("AZURE_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = get_secret("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = get_secret("SUPABASE_SECRET_KEY")
MAX_OCR_COUNT = 1000

client = DocumentAnalysisClient(
    endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
)
supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

no_record = False

# 金額抽出用
AMOUNT_PRIORITY_KEYWORDS = [
    "支払合計",
    "TOTAL",
    "Total",
    "請求額",
    "請求金額",
    "領収額",
    "領収金額",
]

DATE_KEYWORDS = [
    "発行日",
    "注文日",
]

# 通貨記号
CURRENCY_SYMBOLS = [
    "¥",
    "￥",
    "円",
]

IGNORE_WORDS = [
    "領収",
    "領",
    "請求",
    "合計",
    "小計",
    "消費税",
    "税込",
    "税",
    "番号",
    "TEL",
    "電話",
    "日時",
    "印刷",
    "担当",
    "内訳",
    "但",
    "No.",
    "クレジットカード",
    "日付",
    "として",
    "お買い上げ",
    "ありがとうございました",
    "年",
    "メータ",
    "代金",
    "金額",
    "¥",
    "￥",
    "円",
    "番号",
    "車番",
    "%",
    "割引",
    "丁目",
    "大阪府",
    "号室",
    "支払",
    "明細",
    "様",
    "責No",
    "ビルディング",
]
