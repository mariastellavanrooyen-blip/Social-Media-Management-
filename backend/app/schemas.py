from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import ClientStatus


class ClientBase(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None
    phone: str | None = None
    status: ClientStatus = ClientStatus.lead
    notes: str | None = None
    last_contact_date: date | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    company: str | None = None
    phone: str | None = None
    status: ClientStatus | None = None
    notes: str | None = None
    last_contact_date: date | None = None


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# --- Upload / merge / send (phase 2) ---


class UploadPreview(BaseModel):
    upload_id: str
    columns: list[str]
    row_count: int
    preview_rows: list[dict[str, str]]


class MergePreviewRequest(BaseModel):
    mapping: dict[str, str]
    subject: str
    body: str
    sample_size: int = 3


class MergePreviewItem(BaseModel):
    row_index: int
    recipient_email: str
    subject: str
    body: str
    is_suppressed: bool


class MergePreviewResponse(BaseModel):
    total_rows: int
    unknown_fields: list[str]
    items: list[MergePreviewItem]


class TemplateIn(BaseModel):
    subject: str
    body: str


class TemplateOut(TemplateIn):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime


class SuppressionIn(BaseModel):
    email: EmailStr
    reason: str | None = None


class SuppressionOut(SuppressionIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class SendStartRequest(BaseModel):
    upload_id: str
    mapping: dict[str, str]
    subject: str
    body: str


class SendJobOut(BaseModel):
    job_id: str
    status: str
    total: int
    sent: int
    failed: int
    skipped_suppressed: int
    skipped_invalid: int
    error: str | None = None
