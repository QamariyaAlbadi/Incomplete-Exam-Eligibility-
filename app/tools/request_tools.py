"""Fetches a Request + Incomplete_Exam pair
get_raise_capacity_request (app/tools/request_tools.py) -- two separate lookups so a
request that doesn't exist at all gives a different, more useful error than a request
that exists but isn't an Incomplete Exam request.
"""

from sqlalchemy import text

from app.exceptions import NotIncompleteExamRequestError, RequestNotFoundError
from app.services.database import get_connection


def get_incomplete_exam_request(request_id: str) -> dict:
    request_query = text(
        'SELECT "Request_ID", "Student_ID", "Request_Type", "Request_Date", '
        '"Submission_Time", "Current_Status", "Description" '
        'FROM "Request" WHERE "Request_ID" = :rid'
    )
    # NOTE: Proof_File_URL is not selected here -- that column doesn't exist yet in
    # the live Incomplete_Exam table (it would need Shaikha to add it in Supabase).
    # The local-file lookup (app/knowledge_base/proof_documents/) doesn't depend on
    # this column at all, so nothing is lost by leaving it out for now. Add
    # '"Proof_File_URL", ' back into the SELECT list below once that column exists.
    incomplete_exam_query = text(
        'SELECT "Request_ID", "Reason", "Proof", "Missed_Exam_Date", '
        '"Missed_Exam_Time", "Course_ID", "Section_ID", "Term", "Exam_Type" '
        'FROM "Incomplete_Exam" WHERE "Request_ID" = :rid'
    )

    with get_connection() as conn:
        request_row = conn.execute(request_query, {"rid": request_id}).mappings().first()
        if request_row is None:
            raise RequestNotFoundError(f"No Request found for Request_ID={request_id!r}.")

        exam_row = conn.execute(incomplete_exam_query, {"rid": request_id}).mappings().first()
        if exam_row is None:
            raise NotIncompleteExamRequestError(
                f"Request_ID={request_id!r} exists (Request_Type="
                f"{request_row['Request_Type']!r}) but has no matching Incomplete_Exam row."
            )

    return {**dict(request_row), **dict(exam_row)}
