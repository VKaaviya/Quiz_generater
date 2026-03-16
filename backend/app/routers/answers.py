"""
answers.py
────────────────────────────────────────────────────
POST /submit-answer  — accept student answer, store it,
                       run adaptive difficulty internally.
                       Returns correct/wrong + message only.
                       Difficulty level is HIDDEN from response.

GET  /progress/{student_id} — internal/admin use only.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question, StudentAnswer, StudentTopicState
from app.schemas import AnswerPayload, AnswerResponse, StudentProgressResponse, TopicProgress
from app.services.adaptive import update_difficulty, difficulty_name, build_event_message

router = APIRouter()


@router.post(
    "/submit-answer",
    response_model=AnswerResponse,
    summary="Submit a student answer",
)
def submit_answer(
    payload: AnswerPayload,
    db: Session = Depends(get_db),
):
    """
    Accepts the student's answer.
    - Stores student_id, question_id, selected_answer, is_correct in DB.
    - Runs adaptive difficulty algorithm internally (hidden from user).
    - Returns: correct (bool), correct_answer, message only.
    - next_difficulty and streak are tracked but NOT exposed to the frontend.
    """
    question = db.get(Question, payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {payload.question_id} not found")

    # Case-insensitive comparison
    is_correct = payload.selected_answer.strip().lower() == question.answer.strip().lower()
    topic      = question.topic or "General"

    # Fetch or create per-student per-topic adaptive state
    state = db.query(StudentTopicState).filter_by(
        student_id=payload.student_id, topic=topic
    ).first()

    if not state:
        state = StudentTopicState(
            student_id=payload.student_id,
            topic=topic,
            level=0,
            streak=0,
            total=0,
            correct=0,
        )
        db.add(state)

    # Run adaptive algorithm — updates level and streak silently
    new_level, new_streak, shifted = update_difficulty(
        state.level, state.streak, is_correct
    )

    state.level      = new_level
    state.streak     = new_streak
    state.total     += 1
    if is_correct:
        state.correct += 1
    state.updated_at = datetime.utcnow()

    # Store answer record
    db.add(StudentAnswer(
        answer_id=str(uuid.uuid4()),
        student_id=payload.student_id,
        question_id=payload.question_id,
        selected_answer=payload.selected_answer,
        is_correct=is_correct,
        difficulty_at=question.difficulty,
    ))
    db.commit()

    # Build user-facing message — no difficulty info exposed
    if is_correct:
        message = "Well done! Keep it up."
    else:
        message = f"The correct answer is: {question.answer}"

    accuracy = round(state.correct / state.total * 100, 1) if state.total > 0 else 0.0

    return AnswerResponse(
        correct=is_correct,
        correct_answer=question.answer,
        message=message,
        accuracy=accuracy,
    )


@router.get(
    "/progress/{student_id}",
    response_model=StudentProgressResponse,
    summary="Get student progress (admin/internal use)",
)
def get_progress(student_id: str, db: Session = Depends(get_db)):
    """Returns per-topic accuracy and adaptive difficulty state for a student."""
    states = db.query(StudentTopicState).filter_by(student_id=student_id).all()

    if not states:
        raise HTTPException(status_code=404, detail=f"No progress found for student '{student_id}'")

    topics = [
        TopicProgress(
            topic=s.topic,
            level=s.level,
            difficulty=difficulty_name(s.level),
            streak=s.streak,
            total=s.total,
            correct=s.correct,
            accuracy=round(s.correct / s.total * 100, 1) if s.total > 0 else 0.0,
        )
        for s in states
    ]

    return StudentProgressResponse(student_id=student_id, topics=topics)
