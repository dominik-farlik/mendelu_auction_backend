import os
import uuid
from typing import Optional

from fastapi import UploadFile, HTTPException
from starlette import status

from config import get_settings

settings = get_settings()

MAX_FILE_SIZE = 10 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".gif": "gif",
    ".webp": "webp",
}


def _detect_image_type(header: bytes) -> str | None:
    """Rozpozná typ obrázku podle prvních bajtů souboru."""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def save_upload_file(file: Optional[UploadFile]) -> str | None:
    """Ověří a uloží nahraný obrázek na disk a vrátí relativní cestu k němu."""
    if not file:
        return None

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Neplatný název souboru.")

    extension = os.path.splitext(file.filename)[1].lower()
    expected_type = ALLOWED_EXTENSIONS.get(extension)
    if not expected_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nepodporovaný formát souboru. Povolené jsou JPG, PNG, GIF a WEBP."
        )

    header = file.file.read(12)
    file.file.seek(0)
    if _detect_image_type(header) != expected_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Obsah souboru neodpovídá obrázku daného formátu."
        )

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_path = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"

    written = 0
    try:
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(CHUNK_SIZE):
                written += len(chunk)
                if written > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Soubor je příliš velký (maximum je {MAX_FILE_SIZE // (1024 * 1024)} MB)."
                    )
                buffer.write(chunk)
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    except Exception:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nepodařilo se uložit soubor na server."
        )

    return str(file_path)


def delete_files(paths: list[str]) -> None:
    """Smaže soubory z disku; chyby jen ignoruje, aby nerozbily už uložená data."""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                print(f"Varování: Nepodařilo se smazat soubor {path}: {e}")
