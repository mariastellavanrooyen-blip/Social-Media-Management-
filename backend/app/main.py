from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import Base, engine, get_db
from app.models import ClientStatus

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Solo CRM")


@app.get("/api/clients", response_model=list[schemas.ClientOut])
def list_clients(
    search: str | None = None,
    status: ClientStatus | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_clients(db, search=search, status=status)


@app.post("/api/clients", response_model=schemas.ClientOut, status_code=201)
def create_client(client_in: schemas.ClientCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_client(db, client_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A client with this email already exists")


@app.get("/api/clients/{client_id}", response_model=schemas.ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = crud.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.put("/api/clients/{client_id}", response_model=schemas.ClientOut)
def update_client(client_id: int, client_in: schemas.ClientUpdate, db: Session = Depends(get_db)):
    client = crud.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        return crud.update_client(db, client, client_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A client with this email already exists")


@app.delete("/api/clients/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = crud.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    crud.delete_client(db, client)


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
