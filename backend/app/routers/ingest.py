import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Source, Chunk
from app.schemas import IngestResponse, ChunkOut
from app.services.ingestion import process_pdf

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/peblo_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/ingest", response_model=IngestResponse, summary="Ingest a PDF file")
async def ingest_pdf(
    file: UploadFile = File(..., description="PDF file to ingest"),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF, extract text, chunk it, and store in the database.
    Returns the source record and all extracted chunks.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save to disk temporarily
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = process_pdf(tmp_path, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Persist source
    source_id = str(uuid.uuid4())
    source = Source(
        source_id=source_id,
        filename=result["filename"],
        grade=result.get("grade"),
        subject=result.get("subject"),
        total_chunks=len(result["chunks"]),
    )
    db.add(source)

    # Persist chunks
    chunk_records = []
    for chunk_data in result["chunks"]:
        chunk = Chunk(
            chunk_id=str(uuid.uuid4()),
            source_id=source_id,
            chunk_index=chunk_data["chunk_index"],
            topic=chunk_data["topic"],
            text=chunk_data["text"],
        )
        db.add(chunk)
        chunk_records.append(chunk)

    db.commit()
    db.refresh(source)

    return IngestResponse(
        source_id=source.source_id,
        filename=source.filename,
        grade=source.grade,
        subject=source.subject,
        total_chunks=source.total_chunks,
        chunks=[
            ChunkOut(
                chunk_id=c.chunk_id,
                source_id=c.source_id,
                chunk_index=c.chunk_index,
                topic=c.topic,
                text=c.text,
            )
            for c in chunk_records
        ],
    )
