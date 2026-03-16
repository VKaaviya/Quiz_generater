"""
llm.py
────────────────────────────────────────────────────
Sends the entire PDF chunk to the LLM and extracts
ALL questions from it in a single call.
No limit on question count — the LLM returns every
question present in the content.
"""
import os
import json
import re
from typing import List, Dict, Any


SYSTEM_PROMPT = """You are an educational quiz extractor for a K-12 learning platform.

You will receive the full text of an educational PDF. Your job:
- If the PDF already contains numbered questions → extract ALL of them as structured quiz questions.
- If the PDF is plain educational content → generate appropriate quiz questions from it.

STRICT RULES:
- Return ONLY a valid JSON array. Zero explanation, zero markdown, zero preamble.
- Extract or generate EVERY question — never skip or truncate.
- NEVER create questions about the title, grade level, subject name, or topic header line.
- NEVER produce questions like "This content covers ___" or "This PDF is about ___".
- Assign source_chunk_id exactly as given — do not modify it.
- Assign difficulty: easy (Grade 1-2), easy/medium (Grade 3-4), medium/hard (Grade 5+).

Question type rules (strictly enforced):
- MCQ      : options = exactly 4 strings. answer = one of those 4 strings exactly.
- TrueFalse: options = ["True", "False"]. answer = "True" or "False".
- FillBlank: options = null. question contains ___. answer = missing word/phrase only.

Return format — a JSON array, nothing else:
[
  {
    "question": "...",
    "type": "MCQ",
    "options": ["A", "B", "C", "D"],
    "answer": "B",
    "difficulty": "easy",
    "source_chunk_id": "..."
  }
]"""


def build_user_prompt(chunk_text: str, chunk_id: str, topic: str, grade: int, subject: str) -> str:
    return f"""Extract ALL quiz questions from this educational PDF content.
Return EVERY question — if the PDF has 10 questions return exactly 10, if 15 return 15.

source_chunk_id: {chunk_id}
Grade: {grade or 'unspecified'}
Subject: {subject or 'General'}
Topic: {topic or 'General'}

PDF CONTENT:
\"\"\"
{chunk_text}
\"\"\"

Return a JSON array of ALL questions. Do not skip any question."""


def call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "anthropic":
        return _call_anthropic(prompt)
    elif provider == "openai":
        return _call_openai(prompt)
    elif provider == "gemini":
        return _call_gemini(prompt)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("LLM_API_KEY", ""))
    message = client.messages.create(
        model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("LLM_API_KEY", ""))
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=8192,
        temperature=0.2,
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("LLM_API_KEY", ""))
    m = genai.GenerativeModel(
        model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": 0.2, "max_output_tokens": 8192},
    )
    return m.generate_content(prompt).text


def parse_llm_response(raw: str) -> List[Dict[str, Any]]:
    """Strip markdown fences and extract the JSON array."""
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array in LLM response:\n{raw[:400]}")
    return json.loads(match.group(0))


def validate_question(q: Dict[str, Any]) -> bool:
    """Structural validation — reject malformed questions before saving."""
    required = {"question", "type", "answer", "difficulty", "source_chunk_id"}
    if not required.issubset(q.keys()):
        return False
    if q["type"] not in ("MCQ", "TrueFalse", "FillBlank"):
        return False
    if q["type"] == "MCQ":
        opts = q.get("options")
        if not opts or len(opts) != 4:
            return False
        # answer must be one of the options
        if q["answer"] not in opts:
            return False
    if q["type"] == "TrueFalse":
        if q.get("answer") not in ("True", "False"):
            return False
    # Reject header-style questions
    bad_patterns = [
        r'this (pdf|content|material) (covers?|includes?)',
        r'grade \d+ (covers?|includes?)',
        r'^what (subject|grade|topic)',
    ]
    q_lower = q["question"].lower()
    for pat in bad_patterns:
        if re.search(pat, q_lower):
            return False
    return True


def generate_questions(
    chunk_text: str,
    chunk_id: str,
    topic: str,
    grade: int,
    subject: str,
    n_questions: int = 1,  # ignored — LLM extracts ALL questions
) -> List[Dict[str, Any]]:
    """
    Send entire PDF content to LLM. Returns ALL questions extracted.
    n_questions is kept for API compatibility but not used.
    """
    prompt    = build_user_prompt(chunk_text, chunk_id, topic, grade, subject)
    raw       = call_llm(prompt)
    questions = parse_llm_response(raw)
    valid     = [q for q in questions if validate_question(q)]
    print(f"[LLM] Extracted {len(questions)} questions, {len(valid)} valid after validation")
    return valid
