import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Float, JSON
from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class Source(Base):
    """Represents an ingested PDF document."""
    __tablename__ = "sources"

    source_id   = Column(String, primary_key=True, default=gen_id)
    filename    = Column(String, nullable=False)
    grade       = Column(Integer, nullable=True)
    subject     = Column(String, nullable=True)
    total_chunks = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Chunk(Base):
    """A cleaned text segment extracted from a source PDF."""
    __tablename__ = "chunks"

    chunk_id    = Column(String, primary_key=True, default=gen_id)
    source_id   = Column(String, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    topic       = Column(String, nullable=True)
    text        = Column(Text, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    """A quiz question generated from a content chunk."""
    __tablename__ = "questions"

    question_id     = Column(String, primary_key=True, default=gen_id)
    source_chunk_id = Column(String, nullable=False, index=True)
    topic           = Column(String, nullable=True)
    subject         = Column(String, nullable=True)
    grade           = Column(Integer, nullable=True)
    question_text   = Column(Text, nullable=False)
    question_type   = Column(String, nullable=False)   # MCQ | TrueFalse | FillBlank
    options         = Column(JSON, nullable=True)       # list for MCQ
    answer          = Column(String, nullable=False)
    difficulty      = Column(String, default="easy")   # easy | medium | hard
    embedding       = Column(JSON, nullable=True)       # float list for dedup
    created_at      = Column(DateTime, default=datetime.utcnow)


class StudentTopicState(Base):
    """Per-student per-topic adaptive difficulty state."""
    __tablename__ = "student_topic_state"

    student_id  = Column(String, primary_key=True)
    topic       = Column(String, primary_key=True)
    level       = Column(Integer, default=0)    # 0=easy 1=medium 2=hard
    streak      = Column(Integer, default=0)    # +N = correct run, -N = wrong run
    total       = Column(Integer, default=0)
    correct     = Column(Integer, default=0)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudentAnswer(Base):
    """Record of every answer a student submits."""
    __tablename__ = "student_answers"

    answer_id       = Column(String, primary_key=True, default=gen_id)
    student_id      = Column(String, nullable=False, index=True)
    question_id     = Column(String, nullable=False, index=True)
    selected_answer = Column(String, nullable=False)
    is_correct      = Column(Boolean, nullable=False)
    difficulty_at   = Column(String, nullable=False)   # snapshot of difficulty when answered
    submitted_at    = Column(DateTime, default=datetime.utcnow)
