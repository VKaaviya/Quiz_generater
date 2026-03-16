"""
seed_sample_data.py
────────────────────────────────────────────────────────────────────────────
Populates the Peblo SQLite database with the provided Grade 3 Science sample
content (plants and animals) WITHOUT requiring an LLM API call.

Run once after first launch:
    python seed_sample_data.py

Or point at a custom DB file:
    DATABASE_PATH=./my.db python seed_sample_data.py
"""

import sqlite3
import uuid
import json
import os
from datetime import datetime

DB_PATH = os.getenv("DATABASE_PATH", "./peblo.db")
NOW     = datetime.utcnow().isoformat()


# ── Source document ────────────────────────────────────────────────────────

SOURCE_ID  = str(uuid.uuid4())
SOURCE = {
    "source_id":    SOURCE_ID,
    "filename":     "peblo_pdf_grade3_science_plants_animals.pdf",
    "grade":        3,
    "subject":      "Science",
    "total_chunks": 2,
    "created_at":   NOW,
}

# ── Content chunks ─────────────────────────────────────────────────────────

CHUNK_PLANTS_ID  = str(uuid.uuid4())
CHUNK_ANIMALS_ID = str(uuid.uuid4())

CHUNKS = [
    {
        "chunk_id":    CHUNK_PLANTS_ID,
        "source_id":   SOURCE_ID,
        "chunk_index": 0,
        "topic":       "Plants",
        "text": (
            "Plants are living things that make their own food through a process called "
            "photosynthesis. The leaf is the part of a plant that makes food using sunlight, "
            "water, and carbon dioxide. During photosynthesis, plants release oxygen gas. "
            "The root is the part of the plant that absorbs water and nutrients from the soil. "
            "The stem carries water and food to all parts of the plant. Plants need sunlight "
            "to grow and survive."
        ),
        "created_at": NOW,
    },
    {
        "chunk_id":    CHUNK_ANIMALS_ID,
        "source_id":   SOURCE_ID,
        "chunk_index": 1,
        "topic":       "Animals",
        "text": (
            "Animals are living things that cannot make their own food. Animals that eat only "
            "plants are called herbivores. Examples of herbivores are cows, goats, and deer. "
            "Animals that eat only other animals are called carnivores. The lion is a carnivore. "
            "Birds are animals that can lay eggs. Fish are animals that live in water. "
            "Not all animals can make their own food — they must eat plants or other animals "
            "to get energy."
        ),
        "created_at": NOW,
    },
]

# ── Quiz questions (the 10 provided sample questions) ─────────────────────

QUESTIONS = [
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_PLANTS_ID,
        "topic":           "Plants",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Which part of a plant makes food?",
        "question_type":   "MCQ",
        "options":         json.dumps(["Root", "Leaf", "Stem", "Flower"]),
        "answer":          "Leaf",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_PLANTS_ID,
        "topic":           "Plants",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Plants need sunlight to grow.",
        "question_type":   "TrueFalse",
        "options":         json.dumps(["True", "False"]),
        "answer":          "True",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_ANIMALS_ID,
        "topic":           "Animals",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Animals that eat only plants are called ____.",
        "question_type":   "FillBlank",
        "options":         None,
        "answer":          "Herbivores",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_ANIMALS_ID,
        "topic":           "Animals",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Which animal is a carnivore?",
        "question_type":   "MCQ",
        "options":         json.dumps(["Cow", "Lion", "Goat", "Deer"]),
        "answer":          "Lion",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_PLANTS_ID,
        "topic":           "Plants",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "The part of the plant that absorbs water from soil is the ____.",
        "question_type":   "FillBlank",
        "options":         None,
        "answer":          "Root",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_ANIMALS_ID,
        "topic":           "Animals",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Birds are animals that can lay eggs.",
        "question_type":   "TrueFalse",
        "options":         json.dumps(["True", "False"]),
        "answer":          "True",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_PLANTS_ID,
        "topic":           "Plants",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Which of these is not a plant part?",
        "question_type":   "MCQ",
        "options":         json.dumps(["Leaf", "Root", "Stem", "Wing"]),
        "answer":          "Wing",
        "difficulty":      "medium",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_PLANTS_ID,
        "topic":           "Plants",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Plants release ____ gas during photosynthesis.",
        "question_type":   "FillBlank",
        "options":         None,
        "answer":          "Oxygen",
        "difficulty":      "medium",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_ANIMALS_ID,
        "topic":           "Animals",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "All animals can make their own food.",
        "question_type":   "TrueFalse",
        "options":         json.dumps(["True", "False"]),
        "answer":          "False",
        "difficulty":      "medium",
        "embedding":       None,
        "created_at":      NOW,
    },
    {
        "question_id":     str(uuid.uuid4()),
        "source_chunk_id": CHUNK_ANIMALS_ID,
        "topic":           "Animals",
        "subject":         "Science",
        "grade":           3,
        "question_text":   "Which animal lives in water?",
        "question_type":   "MCQ",
        "options":         json.dumps(["Tiger", "Fish", "Elephant", "Dog"]),
        "answer":          "Fish",
        "difficulty":      "easy",
        "embedding":       None,
        "created_at":      NOW,
    },
]


# ── Database helpers ───────────────────────────────────────────────────────

def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sources (
        source_id   TEXT PRIMARY KEY,
        filename    TEXT NOT NULL,
        grade       INTEGER,
        subject     TEXT,
        total_chunks INTEGER DEFAULT 0,
        created_at  TEXT
    );

    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id    TEXT PRIMARY KEY,
        source_id   TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        topic       TEXT,
        text        TEXT NOT NULL,
        created_at  TEXT
    );

    CREATE TABLE IF NOT EXISTS questions (
        question_id     TEXT PRIMARY KEY,
        source_chunk_id TEXT NOT NULL,
        topic           TEXT,
        subject         TEXT,
        grade           INTEGER,
        question_text   TEXT NOT NULL,
        question_type   TEXT NOT NULL,
        options         TEXT,
        answer          TEXT NOT NULL,
        difficulty      TEXT DEFAULT 'easy',
        embedding       TEXT,
        created_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS student_topic_state (
        student_id  TEXT,
        topic       TEXT,
        level       INTEGER DEFAULT 0,
        streak      INTEGER DEFAULT 0,
        total       INTEGER DEFAULT 0,
        correct     INTEGER DEFAULT 0,
        updated_at  TEXT,
        PRIMARY KEY (student_id, topic)
    );

    CREATE TABLE IF NOT EXISTS student_answers (
        answer_id       TEXT PRIMARY KEY,
        student_id      TEXT NOT NULL,
        question_id     TEXT NOT NULL,
        selected_answer TEXT NOT NULL,
        is_correct      INTEGER NOT NULL,
        difficulty_at   TEXT NOT NULL,
        submitted_at    TEXT
    );
    """)


def insert_source(conn, s):
    conn.execute(
        "INSERT OR IGNORE INTO sources VALUES (:source_id,:filename,:grade,:subject,:total_chunks,:created_at)",
        s,
    )


def insert_chunk(conn, c):
    conn.execute(
        "INSERT OR IGNORE INTO chunks VALUES (:chunk_id,:source_id,:chunk_index,:topic,:text,:created_at)",
        c,
    )


def insert_question(conn, q):
    conn.execute(
        """INSERT OR IGNORE INTO questions
           (question_id,source_chunk_id,topic,subject,grade,
            question_text,question_type,options,answer,difficulty,embedding,created_at)
           VALUES
           (:question_id,:source_chunk_id,:topic,:subject,:grade,
            :question_text,:question_type,:options,:answer,:difficulty,:embedding,:created_at)""",
        q,
    )


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    create_tables(conn)
    print("Tables ensured.")

    insert_source(conn, SOURCE)
    print(f"Source inserted: {SOURCE['filename']} (grade {SOURCE['grade']})")

    for chunk in CHUNKS:
        insert_chunk(conn, chunk)
    print(f"{len(CHUNKS)} chunks inserted.")

    for q in QUESTIONS:
        insert_question(conn, q)
    print(f"{len(QUESTIONS)} questions inserted.")

    conn.commit()
    conn.close()

    print("\nSeed complete. Verify with:")
    print(f"  sqlite3 {DB_PATH} \"SELECT question_type, difficulty, question_text FROM questions;\"")
    print("\nOr via API once the server is running:")
    print("  GET http://localhost:8000/quiz?subject=Science&grade=3")
    print("  GET http://localhost:8000/quiz?topic=Plants")
    print("  GET http://localhost:8000/quiz?topic=Animals&difficulty=easy")


if __name__ == "__main__":
    main()
