# Academic Eligibility Evaluation Agent For Incomplete Exam

Given an `Incomplete_Exam` request ID, the agent collects verified evidence from the
database and the approved policy, then asks Gemini for one recommendation: `APPROVE`,
`REJECT`, or `MANUAL_REVIEW`, with an explanation for each check. The agent only
recommends -- the final decision is made by the HOD/administrator.

## What it checks

1. **Enrollment** -- the student has a `Takes` record for the referenced
   Course_ID/Section_ID/Term.
2. **Submission window** -- the request was filed within 4 working days of
   `Missed_Exam_Date` (Friday/Saturday excluded; public holidays are not yet accounted
   for, and this is flagged in the evidence as `holiday_calendar_checked: false`).
3. **Proof** -- proof was provided, and an actual supporting document is attached and
   reviewed by Gemini. A text description in `Proof` alone is treated as unverified.
4. **Reason validity** -- the student's stated reason (`Request.Description`, falling
   back to `Incomplete_Exam.Reason`) is judged by Gemini against the policy's acceptable
   proof categories and explicitly invalid reasons (misreading the schedule,
   non-emergency personal travel, standard job obligations).
5. **Exam type** -- the exam type is not an excluded type (currently confirmed: none are
   excluded; only Midterm and Final exist).

The agent never invents enrollment records or policy thresholds. Missing, unclear, or
unverifiable evidence routes to `MANUAL_REVIEW` rather than being treated as a failure.

## Architecture

- **Python**, run as a local CLI.
- **Database**: Supabase PostgreSQL, accessed **read-only** (SELECT only) via SQLAlchemy
  2.x + `psycopg` 3 (`app/services/database.py`).
- **Gemini** (`google-genai`) is the decision-making layer. Python collects and computes
  deterministic evidence only; it does not combine that evidence into a recommendation.
  Gemini is not given tool access -- it receives the evidence package, explicit decision
  rules, and any proof documents as attachments, and returns a structured JSON response
  (`app/services/gemini.py`).
- If Gemini is unavailable (no API key, network error, unparsable response), the
  recommendation falls back to `MANUAL_REVIEW`.

### Pipeline

```
Request ID
-> get Request + Incomplete_Exam details
-> get student info
-> verify enrollment (Takes table)
-> evaluate against the incomplete-exam policy (window, proof provided, exam type)
-> load proof document(s)
-> build evidence package
-> Gemini: recommendation + per-check explanation
```

## Project layout

| File | Purpose |
|---|---|
| `app/agent.py` | Pipeline, evidence package, CLI report output |
| `app/config.py` | Loads `.env` settings |
| `app/exceptions.py` | Agent error types |
| `app/services/database.py` | Read-only database connection |
| `app/services/gemini.py` | Decision rules, response schema, Gemini call |
| `app/tools/request_tools.py` | Fetches the Request + Incomplete_Exam row |
| `app/tools/student_tools.py` | Fetches student info |
| `app/tools/enrollment_tools.py` | Looks up the matching Takes record |
| `app/tools/exam_policy_tools.py` | Loads the policy and computes deterministic checks |
| `app/tools/proof_file_tools.py` | Loads proof documents (local test files or `Proof_File_URL`) |
| `app/knowledge_base/incomplete_exam_policy.json` | Approved incomplete-exam policy |
| `app/knowledge_base/proof_documents/` | Local test proof documents (see its README) |
| `tests/test_agent.py` | CLI test harness |
| `api.py`, `test_page.html` | Local-only test API and browser test page |

## Setup

```
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

```
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash
DATABASE_URL=...
```

## Run with

```
python -m app.agent <request_id>
```

or

```
python tests/test_agent.py <request_id>
```

This prints a formatted report followed by the full JSON result.

### Test page (optional, local only)

```
pip install fastapi uvicorn python-multipart
uvicorn api:app --reload --port 8000
```

Then open `test_page.html` in a browser. The page can also attach extra documents for a
single evaluation; these are held in memory only and never saved.

## Known limitations

- `Proof_File_URL` does not exist yet in the live `Incomplete_Exam` table, so proof
  documents currently come only from `app/knowledge_base/proof_documents/`.
- Public holidays are not excluded from the working-day count (no holiday calendar in
  the schema).
- The "before final grades are approved" alternative deadline can't be checked, because
  no grade-approval date is stored.
