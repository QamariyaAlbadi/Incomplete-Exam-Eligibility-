"""Verifies the student was enrolled in the Course_ID/Section_ID/Term that the
Incomplete_Exam request references, via the "Takes" table, matched on the
(Student_ID, Course_ID, Section_ID, Term) combination.

Design choice: this returns what was found (a Takes row, or None) as evidence. It does
NOT decide whether "no matching Takes row" means REJECT (student was never in this
section) or MANUAL_REVIEW (a record-keeping gap) -- that judgment is left to Gemini,
consistent with how every other ambiguous call in this agent is handled.
"""

from sqlalchemy import text

from app.services.database import get_connection


def get_enrollment(student_id: str, course_id: int, section_id: str, term: int) -> dict | None:
    query = text(
        'SELECT "Student_ID", "Course_ID", "Section_ID", "Term", "Grade" '
        'FROM "Takes" '
        'WHERE "Student_ID" = :sid AND "Course_ID" = :cid '
        'AND "Section_ID" = :secid AND "Term" = :term'
    )
    with get_connection() as conn:
        row = conn.execute(
            query,
            {"sid": student_id, "cid": course_id, "secid": section_id, "term": term},
        ).mappings().first()

    return dict(row) if row is not None else None
