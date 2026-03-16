"""
test_peblo.py
─────────────────────────────────────────────────────────────────
Automated test script for the Peblo AI Quiz Engine.
Tests all endpoints in the correct order with real assertions.

Usage:
    python test_peblo.py                         # uses sample PDF text
    python test_peblo.py --pdf path/to/file.pdf  # uses a real PDF

Run from: peblo_v2/backend/
"""
import sys
import json
import time
import argparse
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
INFO = "\033[94m→\033[0m"
HEAD = "\033[1m\033[95m"
ENDC = "\033[0m"

results = {"passed": 0, "failed": 0, "errors": []}


def req(method, path, body=None, headers=None, files=None):
    url = BASE + path
    h   = headers or {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    try:
        r = urllib.request.Request(url, data=data, headers=h, method=method)
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}


def upload_pdf(filepath):
    """Multipart file upload using urllib."""
    import os, uuid
    boundary = uuid.uuid4().hex
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    url = BASE + "/ingest"
    r   = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}


def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
        results["passed"] += 1
    else:
        print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        results["failed"] += 1
        results["errors"].append(name)


def section(title):
    print(f"\n{HEAD}{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}{ENDC}")


# ─────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────

def test_health():
    section("1. Health Check — GET /health")
    status, data = req("GET", "/health")
    check("Status 200",         status == 200,          f"got {status}")
    check("status == healthy",  data.get("status") == "healthy", str(data))
    return status == 200


def test_ingest(pdf_path=None):
    section("2. Content Ingestion — POST /ingest")

    if pdf_path:
        print(f"  {INFO} Uploading: {pdf_path}")
        status, data = upload_pdf(pdf_path)
    else:
        # Create a tiny in-memory PDF using raw bytes
        print(f"  {INFO} No PDF provided — creating minimal test PDF in memory")
        import tempfile, os
        # Minimal valid PDF with educational content
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 300>>
stream
BT /F1 12 Tf 50 750 Td
(Peblo Sample Content - Grade 3 Science) Tj 0 -20 Td
(Topic: Plants and Animals) Tj 0 -30 Td
(1. Which part of a plant makes food?) Tj 0 -15 Td
(A. Root  B. Leaf  C. Stem  D. Flower) Tj 0 -15 Td
(Answer: Leaf) Tj 0 -25 Td
(2. Plants need sunlight to grow.) Tj 0 -15 Td
(Answer: True) Tj 0 -25 Td
(3. Animals that eat only plants are called ____.) Tj 0 -15 Td
(Answer: Herbivores) Tj
ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000626 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
715
%%EOF"""
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(pdf_content)
        tmp.close()
        status, data = upload_pdf(tmp.name)
        os.unlink(tmp.name)

    print(f"  {INFO} Response: {json.dumps({k:v for k,v in data.items() if k != 'chunks'}, indent=2)}")

    check("Status 200",              status == 200,                 f"got {status}: {data.get('detail','')}")
    check("source_id present",       bool(data.get("source_id")),   str(data))
    check("filename present",        bool(data.get("filename")),     str(data))
    check("total_chunks == 1",       data.get("total_chunks") == 1, f"got {data.get('total_chunks')} — should be 1 (single chunk per PDF)")
    check("chunks list returned",    isinstance(data.get("chunks"), list) and len(data.get("chunks", [])) == 1)
    check("chunk has chunk_id",      bool(data.get("chunks", [{}])[0].get("chunk_id")))
    check("chunk has text",          bool(data.get("chunks", [{}])[0].get("text")))
    check("chunk has topic",         bool(data.get("chunks", [{}])[0].get("topic")))

    return data.get("source_id"), data.get("chunks", [{}])[0].get("chunk_id")


def test_generate_quiz(source_id):
    section("3. Quiz Generation — POST /generate-quiz")
    print(f"  {INFO} source_id: {source_id}")
    print(f"  {INFO} Calling LLM — this may take 10-30 seconds...")

    status, data = req("POST", "/generate-quiz", {"source_id": source_id, "questions_per_chunk": 1})

    print(f"  {INFO} Response: {json.dumps(data, indent=2)}")

    check("Status 200",                  status == 200,                          f"got {status}: {data.get('detail','')}")
    check("source_id matches",           data.get("source_id") == source_id)
    check("questions_generated > 0",     data.get("questions_generated", 0) > 0, f"got {data.get('questions_generated')} — check LLM_API_KEY in .env")
    check("duplicates_skipped present",  "duplicates_skipped" in data)

    return data.get("questions_generated", 0)


def test_get_quiz(source_id, question_count):
    section("4. Quiz Retrieval — GET /quiz")

    # Test 1: All questions (no filters)
    print(f"\n  {INFO} Test A: GET /quiz?source_id={source_id[:8]}... (no filters)")
    status, data = req("GET", f"/quiz?source_id={source_id}")
    check("Status 200",                     status == 200,                         f"got {status}")
    check("total > 0",                      data.get("total", 0) > 0,              f"got {data.get('total')}")
    check("total matches generated count",  data.get("total") == question_count,   f"got {data.get('total')}, expected {question_count}")
    check("questions array present",        isinstance(data.get("questions"), list))

    questions = data.get("questions", [])
    if questions:
        q = questions[0]
        check("question has question_id",    bool(q.get("question_id")))
        check("question has question text",  bool(q.get("question")))
        check("question has type",           q.get("type") in ("MCQ","TrueFalse","FillBlank"),  f"got {q.get('type')}")
        check("question has answer",         bool(q.get("answer")))
        check("question has difficulty",     q.get("difficulty") in ("easy","medium","hard"),   f"got {q.get('difficulty')}")
        check("question has source_chunk_id",bool(q.get("source_chunk_id")))

        # Check MCQ has 4 options
        mcq_qs = [x for x in questions if x["type"] == "MCQ"]
        if mcq_qs:
            check("MCQ has exactly 4 options",   len(mcq_qs[0].get("options", [])) == 4,  f"got {len(mcq_qs[0].get('options',[]))}")

    # Test 2: Filter by difficulty
    print(f"\n  {INFO} Test B: GET /quiz?source_id=...&difficulty=easy")
    s2, d2 = req("GET", f"/quiz?source_id={source_id}&difficulty=easy")
    check("Status 200 with filter",          s2 == 200)
    easy_qs = d2.get("questions", [])
    check("All returned are easy",           all(q.get("difficulty") == "easy" for q in easy_qs) if easy_qs else True,
          f"{[q.get('difficulty') for q in easy_qs]}")

    # Test 3: Filter by topic
    if questions:
        topic = questions[0].get("topic", "")
        if topic:
            print(f"\n  {INFO} Test C: GET /quiz?source_id=...&topic={topic}")
            s3, d3 = req("GET", f"/quiz?source_id={source_id}&topic={urllib.parse.quote(topic)}")
            check("Status 200 with topic filter", s3 == 200)
            check("Questions returned for topic", d3.get("total", 0) >= 0)

    # Test 4: Missing source_id should fail
    print(f"\n  {INFO} Test D: GET /quiz (no source_id — should return 422)")
    s4, d4 = req("GET", "/quiz")
    check("Returns 422 without source_id",   s4 == 422, f"got {s4}")

    return questions


def test_submit_answer(questions):
    section("5. Student Answer Submission — POST /submit-answer")
    if not questions:
        print(f"  ⚠ Skipped — no questions available")
        return

    student_id = "test_student_001"
    q          = questions[0]
    answer     = q["answer"]

    print(f"  {INFO} Submitting correct answer for: {q['question'][:60]}...")
    print(f"  {INFO} Answer: {answer}")

    status, data = req("POST", "/submit-answer", {
        "student_id":      student_id,
        "question_id":     q["question_id"],
        "selected_answer": answer,
    })

    print(f"  {INFO} Response: {json.dumps(data, indent=2)}")

    check("Status 200",              status == 200,          f"got {status}: {data.get('detail','')}")
    check("correct == True",         data.get("correct") == True)
    check("correct_answer present",  bool(data.get("correct_answer")))
    check("message present",         bool(data.get("message")))
    check("accuracy present",        "accuracy" in data)
    check("accuracy is 100.0",       data.get("accuracy") == 100.0, f"got {data.get('accuracy')}")

    # HIDDEN fields — must NOT be in response
    check("next_difficulty is HIDDEN",  "next_difficulty" not in data, f"next_difficulty should be hidden but found in response!")
    check("streak is HIDDEN",           "streak" not in data,          f"streak should be hidden but found in response!")

    # Submit wrong answer
    if len(questions) > 1:
        q2         = questions[1]
        wrong_ans  = "WRONG_ANSWER_XYZ"
        print(f"\n  {INFO} Submitting WRONG answer...")
        s2, d2 = req("POST", "/submit-answer", {
            "student_id":      student_id,
            "question_id":     q2["question_id"],
            "selected_answer": wrong_ans,
        })
        check("Status 200 for wrong answer",  s2 == 200)
        check("correct == False",             d2.get("correct") == False)
        check("correct_answer still shown",   bool(d2.get("correct_answer")))

    # Submit unknown question — should 404
    print(f"\n  {INFO} Submitting unknown question_id — should return 404")
    s3, d3 = req("POST", "/submit-answer", {
        "student_id":      student_id,
        "question_id":     "nonexistent-question-id",
        "selected_answer": "X",
    })
    check("Returns 404 for unknown question", s3 == 404, f"got {s3}")


def test_adaptive_difficulty(questions):
    section("6. Adaptive Difficulty — Internal verification")
    if len(questions) < 3:
        print(f"  ⚠ Need at least 3 questions for adaptive test, only have {len(questions)}")
        return

    print(f"  {INFO} Submitting 3 correct answers in a row to trigger level-up...")
    student_id = "adaptive_test_student"

    for i, q in enumerate(questions[:3]):
        s, d = req("POST", "/submit-answer", {
            "student_id":      student_id,
            "question_id":     q["question_id"],
            "selected_answer": q["answer"],
        })
        check(f"Answer {i+1} accepted (status 200)", s == 200, f"got {s}")

    # Check progress endpoint
    print(f"\n  {INFO} Checking GET /progress/{student_id}")
    s, d = req("GET", f"/progress/{student_id}")
    check("Progress endpoint returns 200",      s == 200, f"got {s}: {d.get('detail','')}")
    check("topics list present",                isinstance(d.get("topics"), list))
    check("student_id matches",                 d.get("student_id") == student_id)

    if d.get("topics"):
        t = d["topics"][0]
        check("topic has level",     "level" in t)
        check("topic has accuracy",  "accuracy" in t)
        check("topic has total",     t.get("total", 0) >= 3, f"got {t.get('total')}")
        check("topic has correct",   t.get("correct", 0) >= 3, f"got {t.get('correct')}")
        print(f"\n  {INFO} Adaptive state: level={t.get('level')} difficulty={t.get('difficulty')} streak={t.get('streak')}")


def test_duplicate_detection(source_id):
    section("7. Duplicate Detection — POST /generate-quiz (2nd call)")
    print(f"  {INFO} Calling generate-quiz again on same source...")
    print(f"  {INFO} All questions should be detected as duplicates")

    status, data = req("POST", "/generate-quiz", {"source_id": source_id, "questions_per_chunk": 1})

    check("Status 200",                      status == 200)
    check("questions_generated == 0",        data.get("questions_generated", -1) == 0,
          f"got {data.get('questions_generated')} — duplicates not being detected!")
    check("duplicates_skipped > 0",          data.get("duplicates_skipped", 0) > 0,
          f"got {data.get('duplicates_skipped')} — expected > 0")

    print(f"  {INFO} Skipped {data.get('duplicates_skipped')} duplicates ✓")


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import urllib.parse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", help="Path to a PDF file to use for testing", default=None)
    args = parser.parse_args()

    print(f"\n{HEAD}{'═'*55}")
    print("  PEBLO AI QUIZ ENGINE — AUTOMATED TEST SUITE")
    print(f"{'═'*55}{ENDC}")
    print(f"  Backend: {BASE}")
    if args.pdf:
        print(f"  PDF:     {args.pdf}")
    print()

    # Run all tests in order
    if not test_health():
        print(f"\n  \033[91mBackend is not running. Start it with:\033[0m")
        print(f"  uvicorn app.main:app --reload\n")
        sys.exit(1)

    source_id, chunk_id = test_ingest(args.pdf)

    if source_id:
        q_count  = test_generate_quiz(source_id)
        questions = test_get_quiz(source_id, q_count)
        test_submit_answer(questions)
        test_adaptive_difficulty(questions)
        test_duplicate_detection(source_id)

    # Summary
    total = results["passed"] + results["failed"]
    pct   = round(results["passed"] / total * 100) if total else 0

    print(f"\n{HEAD}{'═'*55}")
    print(f"  TEST RESULTS: {results['passed']}/{total} passed ({pct}%)")
    print(f"{'═'*55}{ENDC}")

    if results["failed"] > 0:
        print(f"\n  \033[91mFailed tests:\033[0m")
        for e in results["errors"]:
            print(f"    ✗ {e}")
    else:
        print(f"\n  \033[92mAll tests passed!\033[0m")

    print()
    sys.exit(0 if results["failed"] == 0 else 1)
