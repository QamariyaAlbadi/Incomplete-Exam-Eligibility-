"""Student lookups, app/tools/student_tools.py."""

from sqlalchemy import text

from app.exceptions import StudentNotFoundError
from app.services.database import get_connection


def get_student_academic_info(student_id: str) -> dict:
    query = text(
        'SELECT "Student_ID", "Student_Name", "Student_Email", "CGPA", '
        '"Completed_Hours", "Program_ID" '
        'FROM "Student" WHERE "Student_ID" = :sid'
    )
    with get_connection() as conn:
        row = conn.execute(query, {"sid": student_id}).mappings().first()

    if row is None:
        raise StudentNotFoundError(f"No Student found for Student_ID={student_id!r}.")

    return dict(row)
