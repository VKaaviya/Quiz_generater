from dotenv import load_dotenv
load_dotenv()                  # ← add this BEFORE any other app imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import ingest, quiz, answers

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Peblo AI Quiz Engine",
    description="Content ingestion and adaptive quiz generation platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(quiz.router, tags=["Quiz"])
app.include_router(answers.router, tags=["Answers"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Peblo AI Quiz Engine is running"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
