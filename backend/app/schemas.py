"""
schemas.py — Pydantic request/response models.
Difficulty is tracked internally but hidden from AnswerResponse.
"""
from typing import List, Optional
from pydantic import BaseModel


# ── Ingestion ──────────────────────────────────────────────────────────────

class ChunkOut(BaseModel):
    chunk_id:    str
    source_id:   str
    chunk_index: int
    topic:       Optional[str]
    text:        str
    class Config:
        from_attributes = True


class IngestResponse(BaseModel):
    source_id:    str
    filename:     str
    grade:        Optional[int]
    subject:      Optional[str]
    total_chunks: int
    chunks:       List[ChunkOut]


# ── Quiz Generation ────────────────────────────────────────────────────────

class GenerateQuizRequest(BaseModel):
    source_id:           str
    questions_per_chunk: int = 1  # always 1 — LLM extracts ALL questions from single chunk


class GenerateQuizResponse(BaseModel):
    source_id:           str
    questions_generated: int
    duplicates_skipped:  int


# ── Quiz Retrieval ─────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    question_id:     str
    question:        str
    type:            str
    options:         Optional[List[str]]
    answer:          str
    difficulty:      str   # stored in DB for adaptive logic, returned for Swagger testing
    topic:           Optional[str]
    source_chunk_id: str
    class Config:
        from_attributes = True


class QuizResponse(BaseModel):
    total:     int
    questions: List[QuestionOut]


# ── Answer Submission ──────────────────────────────────────────────────────

class AnswerPayload(BaseModel):
    student_id:      str
    question_id:     str
    selected_answer: str


class AnswerResponse(BaseModel):
    correct:        bool
    correct_answer: str
    message:        str    # "Well done!" or "Correct answer is: X"
    accuracy:       float  # student's running accuracy %
    # next_difficulty and streak are intentionally EXCLUDED — hidden from user


# ── Student Progress (internal/admin) ─────────────────────────────────────

class TopicProgress(BaseModel):
    topic:      str
    level:      int
    difficulty: str
    streak:     int
    total:      int
    correct:    int
    accuracy:   float


class StudentProgressResponse(BaseModel):
    student_id: str
    topics:     List[TopicProgress]
