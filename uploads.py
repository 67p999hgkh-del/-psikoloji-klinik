import os
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024


def allowed_photo(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


def save_person_photo(file, subfolder):
    if not file or not file.filename:
        return None

    if not allowed_photo(file.filename):
        raise ValueError("Geçersiz dosya formatı. PNG, JPG, WEBP veya GIF yükleyin.")

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_PHOTO_SIZE:
        raise ValueError("Dosya boyutu 5 MB'dan küçük olmalıdır.")

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = Path("static/uploads") / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / filename
    file.save(filepath)
    return f"uploads/{subfolder}/{filename}"


def photo_url(photo, static_url_for):
    if not photo or photo == "default.jpg":
        return None
    if photo.startswith("http://") or photo.startswith("https://"):
        return photo
    return static_url_for("static", filename=photo)
