from pathlib import Path
from config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, BUCKET_NAME


def load_upload_widget_html(
    base_dir: Path, session_id: str, css_content: str, js_content: str, uuid: str
) -> str:
    template_path = base_dir / "frontend" / "templates" / "upload_widget.html"
    template = template_path.read_text(encoding="utf-8")
    return (
        template.replace("{{SUPABASE_URL}}", SUPABASE_URL)
        .replace("{{SUPABASE_PUBLISHABLE_KEY}}", SUPABASE_PUBLISHABLE_KEY)
        .replace("{{session_id}}", session_id)
        .replace("{{css}}", css_content)
        .replace("{{js}}", js_content)
        .replace("{{BUCKET_NAME}}", BUCKET_NAME)
        .replace("{{uuid}}", uuid)
    )
