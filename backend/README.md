# Peblo AI — Content Ingestion + Adaptive Quiz Engine

A backend system that ingests educational PDFs, generates quiz questions using an LLM, and serves them through a REST API with per-student adaptive difficulty.

---

## Architecture Overview

```
PDF File
   │
   ▼
POST /ingest
   │  PyMuPDF extracts text
   │  Text is cleaned + chunked
   │  Metadata inferred from filename
   │  Chunks stored in DB
   ▼
POST /generate-quiz
   │  Each chunk → LLM prompt
   │  LLM returns MCQ / TrueFalse / FillBlank questions
   │  Questions validated + deduplicated via embeddings
   │  Questions stored in DB with source_chunk_id traceability
   ▼
GET /quiz?topic=shapes&difficulty=easy
   │  Returns filtered questions from DB
   ▼
POST /submit-answer
   │  Records student answer
   │  Compares to stored correct answer
   │  Updates per-student per-topic difficulty state
   │  Returns next difficulty level
   ▼
GET /progress/{student_id}
   └  Returns accuracy + difficulty level per topic
```

---

## Project Structure

```
peblo_quiz_engine/
├── app/
│   ├── main.py              # FastAPI app, routers registration
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models.py            # ORM models (Source, Chunk, Question, ...)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── ingest.py        # POST /ingest
│   │   ├── quiz.py          # POST /generate-quiz, GET /quiz
│   │   └── answers.py       # POST /submit-answer, GET /progress/{id}
│   └── services/
│       ├── ingestion.py     # PDF extraction, cleaning, chunking
│       ├── llm.py           # LLM prompt building + response parsing
│       ├── embeddings.py    # Cosine similarity duplicate detection
│       └── adaptive.py      # Difficulty adjustment algorithm
├── tests/
│   ├── test_adaptive.py
│   ├── test_embeddings.py
│   ├── test_ingestion.py
│   ├── test_llm.py
│   └── test_api.py
├── docs/
│   └── sample_outputs.json
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### 1. Clone and create a virtual environment

```bash
git clone <your-repo-url>
cd peblo_quiz_engine
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

To enable semantic duplicate detection (recommended):

```bash
pip install sentence-transformers
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
LLM_PROVIDER=anthropic          # or "openai"
LLM_API_KEY=your_key_here
LLM_MODEL=claude-sonnet-4-6     # or gpt-4o-mini for OpenAI
DATABASE_URL=sqlite:///./peblo.db
DEDUP_THRESHOLD=0.85
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## API Endpoints

### `POST /ingest`

Upload a PDF file for extraction and chunking.

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@peblo_pdf_grade1_math_numbers.pdf"
```

**Response:**
```json
{
  "source_id": "a1b2c3...",
  "filename": "peblo_pdf_grade1_math_numbers.pdf",
  "grade": 1,
  "subject": "Math",
  "total_chunks": 5,
  "chunks": [...]
}
```

---

### `POST /generate-quiz`

Trigger LLM question generation for an ingested source.

```bash
curl -X POST http://localhost:8000/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{"source_id": "a1b2c3...", "questions_per_chunk": 3}'
```

**Response:**
```json
{
  "source_id": "a1b2c3...",
  "questions_generated": 12,
  "duplicates_skipped": 2
}
```

---

### `GET /quiz`

Retrieve quiz questions with optional filters.

```bash
curl "http://localhost:8000/quiz?topic=shapes&difficulty=easy&limit=5"
```

**Query parameters:**

| Parameter  | Type   | Description                        |
|------------|--------|------------------------------------|
| topic      | string | Filter by topic (partial match)    |
| difficulty | string | easy \| medium \| hard             |
| subject    | string | Filter by subject                  |
| grade      | int    | Filter by grade level              |
| limit      | int    | Max results (default 10, max 100)  |

---

### `POST /submit-answer`

Submit a student's answer and receive adaptive feedback.

```bash
curl -X POST http://localhost:8000/submit-answer \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "S001",
    "question_id": "q1a2b3...",
    "selected_answer": "3"
  }'
```

**Response:**
```json
{
  "correct": true,
  "correct_answer": "3",
  "next_difficulty": "easy",
  "streak": 1,
  "accuracy": 75.0,
  "message": "Correct — 2 more in a row to advance"
}
```

---

### `GET /progress/{student_id}`

View a student's difficulty level and accuracy per topic.

```bash
curl http://localhost:8000/progress/S001
```

---

## Adaptive Difficulty Algorithm

Difficulty is tracked **per student per topic** (not globally).

- Student starts at `easy` for every topic.
- **3 consecutive correct answers** → difficulty increases (easy → medium → hard).
- **3 consecutive wrong answers** → difficulty decreases (hard → medium → easy).
- Streak **resets to 0** when difficulty shifts — the student must prove themselves at the new level.
- The threshold (default: 3) is configurable via the `STREAK_THRESHOLD` constant in `app/services/adaptive.py`.

---

## Duplicate Detection

After each question is generated, its text is converted to an embedding vector and compared against all existing questions using cosine similarity.

- If similarity ≥ `DEDUP_THRESHOLD` (default 0.85), the question is skipped.
- With `sentence-transformers` installed: uses `all-MiniLM-L6-v2` (semantic similarity).
- Without it: falls back to character n-gram hashing (fast, no GPU required).

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite database and do not require a real LLM API key.

---

## Using PostgreSQL (optional)

1. Create a database: `createdb peblo_db`
2. Update `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/peblo_db
   ```
3. Uncomment `psycopg2-binary` in `requirements.txt` and reinstall.

For vector search at scale, install `pgvector` and migrate the `embedding` column to `vector(384)`.

---

## Technology Choices

| Layer        | Choice                        | Reason                                        |
|--------------|-------------------------------|-----------------------------------------------|
| Framework    | FastAPI                       | Async, auto-docs, Pydantic validation         |
| Database     | SQLite / PostgreSQL           | Zero-config default; Postgres for production  |
| LLM          | Anthropic Claude / OpenAI     | Configurable via env vars                     |
| PDF parsing  | PyMuPDF                       | Fast, accurate text extraction                |
| Embeddings   | sentence-transformers         | Local, no extra API calls required            |
| Testing      | pytest + httpx                | Clean, async-compatible test client           |

---

## Sample Outputs

See `docs/sample_outputs.json` for example API responses and the full database schema.
