import uuid
from io import BytesIO
from pathlib import Path

import pandas as pd

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def parse_upload(filename: str, content: bytes) -> pd.DataFrame:
    lower = filename.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(BytesIO(content), dtype=str)
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        df = pd.read_excel(BytesIO(content), dtype=str)
    else:
        raise ValueError("Unsupported file type — please upload a .csv or .xlsx file")
    return df.fillna("").astype(str)


def save_upload(df: pd.DataFrame) -> str:
    upload_id = uuid.uuid4().hex
    df.to_csv(UPLOADS_DIR / f"{upload_id}.csv", index=False)
    return upload_id


def load_upload(upload_id: str) -> pd.DataFrame | None:
    path = UPLOADS_DIR / f"{upload_id}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, dtype=str).fillna("").astype(str)
