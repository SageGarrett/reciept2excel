from datetime import datetime, timedelta
from io import BytesIO
from config import BUCKET_NAME


class SupabaseUploadedFile(BytesIO):
    def __init__(self, file_bytes: bytes, name: str, file_type: str = ""):
        super().__init__(file_bytes)
        self.name = name
        self.type = file_type
        self.size = len(file_bytes)


MIME_MAP = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "pdf": "application/pdf",
    "heic": "image/heic",
    "heif": "image/heif",
}


# supabaseからレシートファイルをダウンロード
def load_uploaded_files_from_supabase(supabase, session_id):
    uploaded_files = []
    bucket = supabase.storage.from_(BUCKET_NAME)
    files = bucket.list(f"{session_id}/receipts")

    for file in files:
        path = f"{session_id}/receipts/{file['name']}"
        file_bytes = bucket.download(path)

        ext = file["name"].split(".")[-1].lower()

        uploaded_files.append(
            SupabaseUploadedFile(
                file_bytes=file_bytes,
                name=file["name"],
                file_type=MIME_MAP.get(ext, ""),
            )
        )

    return uploaded_files


# 保持期間を過ぎたセッションを削除する。
def cleanup_old_sessions(supabase):
    print("cleanup_old_sessions_start")
    session_dirs = supabase.storage.from_(BUCKET_NAME).list()
    print(session_dirs)

    # 保持期間：1時間
    threshold = datetime.now() - timedelta(hours=1)

    for session_dir in session_dirs:
        session_name = session_dir["name"]

        try:
            dt = datetime.strptime(session_name, "%Y%m%d_%H%M%S_%f")

        except ValueError:
            continue

        if dt < threshold:
            cleanup_supabase_files(supabase, session_name)


def cleanup_supabase_files(supabase, session_id):
    bucket = supabase.storage.from_(BUCKET_NAME)
    paths = []

    for prefix in [
        f"{session_id}/receipts",
        f"{session_id}/excel",
    ]:
        files = bucket.list(prefix) or []
        paths.extend(f"{prefix}/{file['name']}" for file in files if file.get("name"))

    # metadata.json は直接指定
    paths.append(f"{session_id}/metadata.json")

    if not paths:
        return {"data": None, "error": None}

    return bucket.remove(paths)
