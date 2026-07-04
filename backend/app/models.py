import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClientStatus(str, enum.Enum):
    lead = "lead"
    contacted = "contacted"
    active = "active"
    closed = "closed"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus), nullable=False, default=ClientStatus.lead
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sends: Mapped[list["EmailSend"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class EmailSend(Base):
    """Log of every bulk-email send attempt. Populated by the send flow (next phase)."""

    __tablename__ = "sends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # sent | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped["Client | None"] = relationship(back_populates="sends")


class SuppressionEntry(Base):
    """Emails that must be skipped on every future bulk send (unsubscribes, bounces, etc.)."""

    __tablename__ = "suppression_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmailTemplate(Base):
    """The single reusable cold-email template, edited in place."""

    __tablename__ = "email_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str] = mapped_column(String(998), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
