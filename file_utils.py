from pdf2image import convert_from_bytes
from PIL import Image

def load_image_from_upload(uploaded_file):
    """
    Streamlitの uploaded_file から PIL.Image を1枚返す
    - PDF: 1ページ目のみ
    - JPG/PNG: そのまま
    """
    if uploaded_file.type == "application/pdf":
        images = convert_from_bytes(uploaded_file.read())
        return images[0]  # 1ページ目だけ使う
    else:
        return Image.open(uploaded_file)
