from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, gmail_client, merge, schemas, send_queue
from app.database import Base, engine, get_db
from app.models import ClientStatus
from app.security import read_unsubscribe_token
from app.upload_store import load_upload, parse_upload, save_upload

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Solo CRM")


# --- Clients ---


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


# --- Upload + column mapping + merge preview ---


@app.post("/api/upload", response_model=schemas.UploadPreview)
async def upload_sheet(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    content = await file.read()
    try:
        df = parse_upload(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded file has no rows")

    upload_id = save_upload(df)
    return schemas.UploadPreview(
        upload_id=upload_id,
        columns=list(df.columns),
        row_count=len(df),
        preview_rows=df.head(5).to_dict(orient="records"),
    )


@app.post("/api/upload/{upload_id}/preview", response_model=schemas.MergePreviewResponse)
def preview_merge(upload_id: str, req: schemas.MergePreviewRequest, db: Session = Depends(get_db)):
    df = load_upload(upload_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    if "email" not in req.mapping or req.mapping["email"] not in df.columns:
        raise HTTPException(status_code=400, detail="Mapping must map 'email' to a valid column")

    unknown: set[str] = set()
    items = []
    for idx, row in df.head(max(req.sample_size, 0)).iterrows():
        context = merge.build_context(row.to_dict(), req.mapping)
        recipient = context.get("email", "").strip()
        rendered_subject = merge.render_template(req.subject, context)
        rendered_body = merge.render_template(req.body, context)
        unknown.update(merge.unknown_fields(req.subject, context))
        unknown.update(merge.unknown_fields(req.body, context))
        items.append(
            schemas.MergePreviewItem(
                row_index=int(idx),
                recipient_email=recipient,
                subject=rendered_subject,
                body=rendered_body,
                is_suppressed=crud.is_suppressed(db, recipient) if recipient else False,
            )
        )

    return schemas.MergePreviewResponse(
        total_rows=len(df), unknown_fields=sorted(unknown), items=items
    )


# --- Email template ---


@app.get("/api/template", response_model=schemas.TemplateOut)
def get_template(db: Session = Depends(get_db)):
    template = crud.get_template(db)
    if template is None:
        return schemas.TemplateOut(subject="", body="", updated_at=datetime.utcnow())
    return template


@app.put("/api/template", response_model=schemas.TemplateOut)
def save_template(template_in: schemas.TemplateIn, db: Session = Depends(get_db)):
    return crud.upsert_template(db, template_in)


# --- Suppression list ---


@app.get("/api/suppression", response_model=list[schemas.SuppressionOut])
def list_suppression(db: Session = Depends(get_db)):
    return crud.list_suppressions(db)


@app.post("/api/suppression", response_model=schemas.SuppressionOut, status_code=201)
def add_suppression(entry_in: schemas.SuppressionIn, db: Session = Depends(get_db)):
    return crud.add_suppression(db, entry_in)


@app.delete("/api/suppression/{entry_id}", status_code=204)
def delete_suppression(entry_id: int, db: Session = Depends(get_db)):
    entry = crud.get_suppression(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Suppression entry not found")
    crud.delete_suppression(db, entry)


@app.get("/api/unsubscribe", response_class=HTMLResponse)
def unsubscribe(token: str, db: Session = Depends(get_db)):
    email = read_unsubscribe_token(token)
    if email is None:
        return HTMLResponse("<h1>Invalid or expired unsubscribe link</h1>", status_code=400)
    crud.add_suppression(db, schemas.SuppressionIn(email=email, reason="unsubscribed"))
    return HTMLResponse(
        f"<h1>You've been unsubscribed</h1><p>{email} will not receive further emails from us.</p>"
    )


# --- Gmail send ---


@app.get("/api/gmail/status")
def gmail_status():
    return {"connected": gmail_client.is_connected()}


@app.post("/api/send/start", response_model=schemas.SendJobOut)
async def start_send(req: schemas.SendStartRequest):
    df = load_upload(req.upload_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    if "email" not in req.mapping or req.mapping["email"] not in df.columns:
        raise HTTPException(status_code=400, detail="Mapping must map 'email' to a valid column")
    job = send_queue.start_job(df, req.mapping, req.subject, req.body)
    return _job_to_out(job)


@app.get("/api/send/jobs/{job_id}", response_model=schemas.SendJobOut)
def get_send_job(job_id: str):
    job = send_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_out(job)


def _job_to_out(job: send_queue.SendJob) -> schemas.SendJobOut:
    return schemas.SendJobOut(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        sent=job.sent,
        failed=job.failed,
        skipped_suppressed=job.skipped_suppressed,
        skipped_invalid=job.skipped_invalid,
        error=job.error,
    )


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
