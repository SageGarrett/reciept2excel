from datetime import date, datetime


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
