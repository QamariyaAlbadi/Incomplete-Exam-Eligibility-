# Academic Eligibility Evaluation Agent For Incomplete Exam (Scaffold)

Scaffolded to follow the same structure and architecture as Agent 3
(Academic Eligibility Evaluation Agent For Raise Capacity). This is an empty skeleton --
the tool implementations, knowledge base content, and Gemini response schema below are
all marked TODO and still need to be filled in.

## Purpose (draft -- confirm against the actual approved rules)

Given an `Incomplete_Exam` request ID, the agent should evaluate whether the request is
eligible, and return one recommendation: `APPROVE`, `REJECT`, or `MANUAL_REVIEW`.

Likely conditions (TODO: confirm these against the actual approved rules before
implementing -- do not assume they're correct or complete):

1. The student was actually enrolled in the referenced Course_ID/Section_ID/Term.
2. The request satisfies the approved incomplete-exam policy (filing deadline relative to
   Missed_Exam_Date, acceptable Proof, valid Exam_Type).

The agent should never invent enrollment records or policy thresholds. Missing or
unverifiable evidence should always route to `MANUAL_REVIEW`, never be silently treated as
a failure -- same principle as Agent 3.

## Architecture

Same as Agent 3:

- **Python**, run as a local CLI (no FastAPI, no LangGraph, no frontend integration yet).
- **Database**: Supabase PostgreSQL, accessed **read-only** via SQLAlchemy 2.x + `psycopg`
  3. `app/services/database.py` is copied as-is from Agent 3 -- it's pure infrastructure
  with no raise-capacity-specific logic.
- **Gemini** (`google-genai`): Gemini is the decision-making layer. Python only collects
  and computes verified, deterministic evidence -- it does not combine that evidence into
  a final recommendation itself. See `app/services/gemini.py` (currently a stub).

## What's implemented vs. what's TODO

| File | Status |
|---|---|
| `.gitignore`, `.env.example` | Done, copied/adapted from Agent 3 |
| `app/services/database.py` | Done, copied from Agent 3 (generic infrastructure) |
| `app/exceptions.py`, `app/config.py` | Adapted skeleton, ready to use |
| `app/tools/request_tools.py` | Stub -- needs the Request + Incomplete_Exam query |
| `app/tools/student_tools.py` | Stub -- needs the student info query |
| `app/tools/enrollment_tools.py` | Stub -- needs the enrollment verification query |
| `app/tools/exam_policy_tools.py` | Stub -- needs the actual incomplete-exam policy defined and implemented |
| `app/knowledge_base/incomplete_exam_policy.json` | Empty placeholder |
| `app/services/gemini.py` | Stub -- needs a response schema and decision rules specific to this agent's checks |
| `app/agent.py` | Stub -- pipeline outline only |
| `tests/test_agent.py` | Empty placeholder |

## Run with

```
python -m app.agent <request_id>
```
(once implemented)
