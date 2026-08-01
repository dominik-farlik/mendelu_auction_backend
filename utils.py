from datetime import datetime, UTC
import shutil
from typing import Optional

from fastapi import UploadFile, HTTPException, status

from config import get_settings


settings = get_settings()


def save_upload_file(file: Optional[UploadFile]) -> Optional[str]:
    """Uloží nahraný soubor na disk a vrátí relativní cestu k němu."""
    if not file:
        return None

    if not file.filename:
        raise HTTPException(status_code=400, detail="Neplatný název souboru.")

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = settings.UPLOAD_DIR / unique_filename

    try:
        with file_path.open("wb") as buffer:
            # noinspection PyTypeChecker
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nepodařilo se uložit soubor na server."
        )

    return str(file_path)