from datetime import date, datetime
from openpyxl import load_workbook


def is_in_fiscal_year(dt: datetime) -> bool:
    today = datetime.today()

    # 今年の年度開始（3/1）
    if today >= datetime(today.year, 3, 1):
        start = datetime(today.year, 3, 1)
    else:
        start = datetime(today.year - 1, 3, 1)

    # 次の年度開始
    end = datetime(start.year + 1, 3, 1)

    return start <= dt < end


def normalize(v):
    if v is None:
        return None

    # 日付（最優先）
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")

    # 数値
    try:
        return int(float(v))
    except:
        # 文字列
        return str(v).strip()
