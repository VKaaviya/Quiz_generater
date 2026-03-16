"""
ingestion.py
────────────────────────────────────────────────────
PDF → extract → clean → ONE single chunk per PDF.
The entire PDF text is stored as a single chunk so
the LLM receives all content at once and can extract
every question without any pagination or splitting.
"""
import re
import os
from typing import List, Dict, Any
from pathlib import Path

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


def extract_text_from_pdf(filepath: str) -> str:
    if PYMUPDF_AVAILABLE:
        return _extract_pymupdf(filepath)
    elif PDFPLUMBER_AVAILABLE:
        return _extract_pdfplumber(filepath)
    else:
        raise RuntimeError("No PDF library found. Install PyMuPDF: pip install pymupdf")


def _extract_pymupdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    pages = [page.get_text("text") for page in doc]
    doc.close()
    return "\n\n".join(pages)


def _extract_pdfplumber(filepath: str) -> str:
    pages = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def clean_text(raw: str) -> str:
    """Light cleaning — preserve structure so LLM can parse questions."""
    text = re.sub(r'\n{4,}', '\n\n\n', raw)   # max 3 blank lines
    text = re.sub(r'[ \t]{2,}', ' ', text)     # collapse spaces
    return text.strip()


def infer_metadata(filename: str) -> Dict[str, Any]:
    """Parse grade and subject from Peblo filename convention."""
    name = Path(filename).stem.lower()
    grade, subject = None, None

    grade_match = re.search(r'grade(\d+)', name)
    if grade_match:
        grade = int(grade_match.group(1))

    subject_map = {
        'english': 'English', 'grammar': 'English',
        'math': 'Math', 'maths': 'Math', 'numbers': 'Math',
        'science': 'Science', 'plants': 'Science', 'animals': 'Science',
    }
    for key, value in subject_map.items():
        if key in name:
            subject = value
            break

    return {"grade": grade, "subject": subject}


def infer_topic(text: str) -> str:
    """Keyword-based topic inference from full PDF text."""
    t = text.lower()
    topic_keywords = {
        "Shapes":     ["triangle", "circle", "square", "rectangle", "shape", "sides", "polygon"],
        "Numbers":    ["count", "number", "digit", "addition", "subtraction", "multiply", "divide"],
        "Plants":     ["plant", "leaf", "root", "stem", "flower", "photosynthesis", "seed"],
        "Animals":    ["animal", "mammal", "reptile", "bird", "fish", "carnivore", "herbivore"],
        "Grammar":    ["noun", "verb", "adjective", "sentence", "grammar", "punctuation", "tense", "plural"],
        "Vocabulary": ["synonym", "antonym", "vocabulary", "opposite", "meaning"],
    }
    best_topic, best_count = "General", 0
    for topic, keywords in topic_keywords.items():
        count = sum(1 for kw in keywords if kw in t)
        if count > best_count:
            best_count = count
            best_topic = topic
    return best_topic


def process_pdf(filepath: str, filename: str) -> Dict[str, Any]:
    """
    Full pipeline:
      extract → clean → store as ONE single chunk.

    One PDF = one chunk = one LLM call = all questions extracted at once.
    """
    raw_text = extract_text_from_pdf(filepath)
    clean    = clean_text(raw_text)
    meta     = infer_metadata(filename)
    topic    = infer_topic(clean)

    return {
        "filename": filename,
        "grade":    meta.get("grade"),
        "subject":  meta.get("subject"),
        "chunks": [
            {
                "chunk_index": 0,
                "topic":       topic,
                "text":        clean,   # entire PDF as one chunk
            }
        ],
    }
