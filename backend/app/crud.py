from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Client, ClientStatus, EmailTemplate, SuppressionEntry
from app.schemas import ClientCreate, ClientUpdate, SuppressionIn, TemplateIn


def get_client(db: Session, client_id: int) -> Client | None:
    return db.get(Client, client_id)


def get_client_by_email(db: Session, email: str) -> Client | None:
    return db.query(Client).filter(Client.email == email).first()


def list_clients(
    db: Session, search: str | None = None, status: ClientStatus | None = None
) -> list[Client]:
    query = db.query(Client)
    if status is not None:
        query = query.filter(Client.status == status)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Client.name.ilike(like), Client.email.ilike(like), Client.company.ilike(like))
        )
    return query.order_by(Client.created_at.desc()).all()


def create_client(db: Session, client_in: ClientCreate) -> Client:
    client = Client(**client_in.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client(db: Session, client: Client, client_in: ClientUpdate) -> Client:
    for field, value in client_in.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


def delete_client(db: Session, client: Client) -> None:
    db.delete(client)
    db.commit()


def get_template(db: Session) -> EmailTemplate | None:
    return db.query(EmailTemplate).order_by(EmailTemplate.id).first()


def upsert_template(db: Session, template_in: TemplateIn) -> EmailTemplate:
    template = get_template(db)
    if template is None:
        template = EmailTemplate(**template_in.model_dump())
        db.add(template)
    else:
        template.subject = template_in.subject
        template.body = template_in.body
    db.commit()
    db.refresh(template)
    return template


def list_suppressions(db: Session) -> list[SuppressionEntry]:
    return db.query(SuppressionEntry).order_by(SuppressionEntry.created_at.desc()).all()


def is_suppressed(db: Session, email: str) -> bool:
    return (
        db.query(SuppressionEntry)
        .filter(SuppressionEntry.email == email.lower())
        .first()
        is not None
    )


def add_suppression(db: Session, entry_in: SuppressionIn) -> SuppressionEntry:
    existing = (
        db.query(SuppressionEntry)
        .filter(SuppressionEntry.email == entry_in.email.lower())
        .first()
    )
    if existing is not None:
        return existing
    entry = SuppressionEntry(email=entry_in.email.lower(), reason=entry_in.reason)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_suppression(db: Session, entry: SuppressionEntry) -> None:
    db.delete(entry)
    db.commit()


def get_suppression(db: Session, entry_id: int) -> SuppressionEntry | None:
    return db.get(SuppressionEntry, entry_id)
