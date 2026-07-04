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
