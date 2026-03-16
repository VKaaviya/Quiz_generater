"""
quiz.py
────────────────────────────────────────────────────
POST /generate-quiz  — send PDF chunk to LLM, extract ALL questions,
                       deduplicate, store. Returns full count.
GET  /quiz           — return ALL questions for a source_id (required param).
                       Supports Swagger UI testing.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Source, Chunk, Question
from app.schemas import (
    GenerateQuizRequest, GenerateQuizResponse,
    QuizResponse, QuestionOut,
)
from app.services.llm import generate_questions
from app.services.embeddings import embed_text, is_duplicate

router = APIRouter()


# ── POST /generate-quiz ───────────────────────────────────────────────────

@router.post(
    "/generate-quiz",
    response_model=GenerateQuizResponse,
    summary="Extract ALL questions from ingested PDF and store them",
)
def generate_quiz(
    payload: GenerateQuizRequest,
    db: Session = Depends(get_db),
):
    """
    Sends the single PDF chunk to the LLM.
    The LLM extracts EVERY question present in the PDF content.
    Duplicate questions are detected via embeddings and skipped.
    Works with any PDF regardless of question count.
    """
    source = db.get(Source, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {payload.source_id} not found")

    chunks = db.query(Chunk).filter(Chunk.source_id == payload.source_id).all()
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for this source. Run /ingest first.")

    # Load existing embeddings for duplicate detection across all PDFs
    existing_rows       = db.query(Question.embedding).filter(Question.embedding.isnot(None)).all()
    existing_embeddings = [row.embedding for row in existing_rows if row.embedding]

    generated_count = 0
    skipped_count   = 0

    # There is always exactly 1 chunk per PDF (entire PDF = single chunk)
    for chunk in chunks:
        print(f"[INFO] Processing chunk {chunk.chunk_id[:8]}... (text length: {len(chunk.text)})")

        try:
            questions = generate_questions(
                chunk_text=chunk.text,
                chunk_id=chunk.chunk_id,
                topic=chunk.topic or "",
                grade=source.grade,
                subject=source.subject or "",
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation failed: {str(e)}"
            )

        print(f"[INFO] LLM returned {len(questions)} valid questions")

        for q in questions:
            # Duplicate detection
            if is_duplicate(q["question"], existing_embeddings):
                skipped_count += 1
                print(f"[DEDUP] Skipped duplicate: {q['question'][:60]}")
                continue

            vec = embed_text(q["question"])

            question = Question(
                question_id=str(uuid.uuid4()),
                source_chunk_id=chunk.chunk_id,
                topic=chunk.topic,
                subject=source.subject,
                grade=source.grade,
                question_text=q["question"],
                question_type=q["type"],
                options=q.get("options"),
                answer=q["answer"],
                difficulty=q.get("difficulty", "easy"),
                embedding=vec,
            )
            db.add(question)
            existing_embeddings.append(vec)
            generated_count += 1

    db.commit()
    print(f"[INFO] Saved {generated_count} questions, skipped {skipped_count} duplicates")

    return GenerateQuizResponse(
        source_id=payload.source_id,
        questions_generated=generated_count,
        duplicates_skipped=skipped_count,
    )


# ── GET /quiz ─────────────────────────────────────────────────────────────

@router.get(
    "/quiz",
    response_model=QuizResponse,
    summary="Get questions for a source PDF with optional filters",
)
def get_quiz(
    source_id:  str            = Query(...,    description="Required — source ID from /ingest"),
    topic:      Optional[str]  = Query(None,   description="Filter by topic e.g. Plants, Grammar"),
    difficulty: Optional[str]  = Query(None,   description="Filter by difficulty: easy | medium | hard"),
    subject:    Optional[str]  = Query(None,   description="Filter by subject e.g. Science, Math"),
    grade:      Optional[int]  = Query(None,   description="Filter by grade level e.g. 3"),
    db: Session = Depends(get_db),
):
    """
    Returns questions for the given source PDF.

    source_id is required — ensures only this PDF's questions are returned.

    Optional filters (all can be combined):
        GET /quiz?source_id=xxx&topic=Plants
        GET /quiz?source_id=xxx&difficulty=easy
        GET /quiz?source_id=xxx&topic=Grammar&difficulty=medium
        GET /quiz?source_id=xxx  (no filters = returns ALL questions)
    """
    # Get all chunk IDs for this source
    chunks    = db.query(Chunk).filter(Chunk.source_id == source_id).all()
    chunk_ids = [c.chunk_id for c in chunks]

    if not chunk_ids:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found for source_id '{source_id}'. Run POST /ingest first."
        )

    # Base query — only this PDF's questions
    q = db.query(Question).filter(Question.source_chunk_id.in_(chunk_ids))

    # Apply optional filters
    if topic:
        q = q.filter(Question.topic.ilike(f"%{topic}%"))
    if difficulty:
        q = q.filter(Question.difficulty == difficulty.lower())
    if subject:
        q = q.filter(Question.subject.ilike(f"%{subject}%"))
    if grade is not None:
        q = q.filter(Question.grade == grade)

    questions = q.all()

    return QuizResponse(
        total=len(questions),
        questions=[
            QuestionOut(
                question_id=qn.question_id,
                question=qn.question_text,
                type=qn.question_type,
                options=qn.options,
                answer=qn.answer,
                difficulty=qn.difficulty,
                topic=qn.topic,
                source_chunk_id=qn.source_chunk_id,
            )
            for qn in questions
        ],
    )