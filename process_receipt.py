def process_receipt(image_path: str) -> dict:
    text = run_ocr(image_path)

    amount = extract_amount(text)
    date = extract_date(text)
    shop = extract_shop(text)

    warning = has_warning(date, amount, shop)

    return {
        "date": date,
        "amount": amount,
        "shop": shop,
        "warning": warning,
        "raw_text": text,
    }