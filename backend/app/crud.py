from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Client, ClientStatus
from app.schemas import ClientCreate, ClientUpdate


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
