"""Incomplete Exam eligibility workflow.

Gemini never chooses which tool to call and is not given tool access.

Pipeline:

    Request ID
    -> get request + Incomplete_Exam details
    -> get student academic info
    -> verify enrollment in the referenced Course_ID/Section_ID/Term (Takes table)
    -> evaluate the request against the approved incomplete-exam policy
       (submission window, proof provided -- deterministic only; reason-category and
       proof-authenticity judgment are left as evidence for Gemini, see
       app/tools/exam_policy_tools.py's module docstring for why)
    -> build evidence package
    -> send evidence package + explicit decision rules to Gemini
    -> Gemini produces a recommendation (APPROVE / REJECT / MANUAL_REVIEW) and
       explains it
    -> return Gemini's recommendation and explanation -- the final decision is made by
       the HOD/administrator, not by this agent

Run with:  python -m app.agent <request_id>
"""

import json
import sys
import textwrap

from app.exceptions import AgentError
from app.services.gemini import get_gemini_decision
from app.tools.enrollment_tools import get_enrollment
from app.tools.exam_policy_tools import evaluate_incomplete_exam_request, get_incomplete_exam_policy
from app.tools.proof_file_tools import fetch_proof_file, get_local_proof_files
from app.tools.request_tools import get_incomplete_exam_request
from app.tools.student_tools import get_student_academic_info

_WIDTH = 72


def _build_evidence_package(request_id: str) -> tuple[dict, list]:
    """Collects and computes all deterministic evidence. Does NOT decide a
    recommendation. Returns (evidence_package, auto_attachments) -- auto_attachments
    holds the real uploaded proof document(s) (from local test files, or fetched from
    Incomplete_Exam.Proof_File_URL as a fallback), ready for Gemini. This is the REAL
    pipeline's own attachment(s), distinct from the test page's manually attached
    files (see evaluate_incomplete_exam_request_workflow below).
    """
    request = get_incomplete_exam_request(request_id)
    student = get_student_academic_info(request["Student_ID"])
    enrollment = get_enrollment(
        request["Student_ID"], request["Course_ID"], request["Section_ID"], request["Term"]
    )
    policy = get_incomplete_exam_policy()
    policy_eval = evaluate_incomplete_exam_request(request, policy)

    # Local files (app/knowledge_base/proof_documents/<request_id>[-<label>].<ext>)
    # are checked first since they need no setup at all; Proof_File_URL is the
    # fallback for when a real upload pipeline exists (currently single-file only).
    proof_file_url = request.get("Proof_File_URL")
    fetched_files = get_local_proof_files(request_id)
    proof_file_source = "local" if fetched_files else None
    if not fetched_files and proof_file_url:
        single = fetch_proof_file(proof_file_url)
        fetched_files = [single] if single else []
        proof_file_source = "url" if fetched_files else None
    auto_attachments = fetched_files

    evidence_package = {
        "request_id": request_id,
        "student": {"Student_ID": student["Student_ID"], "Student_Name": student["Student_Name"]},
        "course_id": request["Course_ID"],
        "section_id": request["Section_ID"],
        "term": request["Term"],
        "checks": {
            "enrollment": {
                "found": enrollment is not None,
                "record": enrollment,
            },
            "submission_window": policy_eval["submission_window"],
            "proof": {
                **policy_eval["proof"],
                "file_url": proof_file_url,
                # True only if at least one file actually existed AND was retrieved --
                # a broken/unreachable URL, or no local file present, is not silently
                # treated as "no proof file was ever meant to exist".
                "file_attached": bool(fetched_files),
                "file_count": len(fetched_files),
                "file_source": proof_file_source,  # "local", "url", or None
            },
            "exam_type": policy_eval["exam_type"],
        },
        # Given to Gemini for its own judgment, not pre-decided here -- see
        # exam_policy_tools.py's module docstring.
        "reason_for_review": policy_eval["reason_for_gemini_review"],
        "policy_reference": {
            "acceptable_proof_categories": policy_eval["acceptable_proof_categories"],
            "explicitly_invalid_reasons": policy_eval["explicitly_invalid_reasons"],
        },
    }
    return evidence_package, auto_attachments


def evaluate_incomplete_exam_request_workflow(request_id: str, attachments=None) -> dict:
    """`attachments` (optional) is for the standalone test page's manually-attached
    files (see app/services/gemini.py's Attachment docstring) -- the real CLI (main(),
    below) never passes this. Either way, any real proof file(s) already linked via
    local test files or Proof_File_URL are fetched and included automatically,
    regardless of `attachments`.
    """
    evidence_package, auto_attachments = _build_evidence_package(request_id)
    all_attachments = (attachments or []) + auto_attachments
    gemini_result = get_gemini_decision(evidence_package, attachments=all_attachments or None)

    return {
        "request_id": request_id,
        "evidence": evidence_package,
        "recommendation": gemini_result["recommendation"],
        "reasoning": gemini_result["reasoning"],
        "checks": gemini_result["checks"],
        "gemini_status": gemini_result["status"],
        "gemini_error": gemini_result["error"],
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _status_tag(satisfied) -> str:
    if satisfied is None:
        return "[ N/A  ]"
    return "[ PASS ]" if satisfied else "[ FAIL ]"

def _found_tag(found: bool) -> str:
    return "[ FOUND    ]" if found else "[ NOT FOUND]"

def _rec_tag(recommendation: str) -> str:
    return {
        "APPROVE": "[ APPROVE ]",
        "REJECT": "[ REJECT  ]",
    }.get(recommendation, f"[ {recommendation} ]")

def _wrap(text, indent: str = "          ") -> str:
    if text in (None, ""):
        return f"{indent}(none)"
    return textwrap.fill(
        str(text), width=_WIDTH - len(indent), initial_indent=indent, subsequent_indent=indent
    )

def _rule(char: str = "-") -> None:
    print(char * _WIDTH)


def _print_report(result: dict) -> None:
    evidence = result["evidence"]
    checks = evidence["checks"]
    enrollment = checks["enrollment"]
    window = checks["submission_window"]
    proof = checks["proof"]
    exam_type = checks["exam_type"]
    student = evidence["student"]
    gemini_explanations = result["checks"]

    _rule("=")
    print("INCOMPLETE EXAM ELIGIBILITY REPORT".center(_WIDTH))
    _rule("=")
    print(f"Request   {result['request_id']}")
    print(f"Student   {student['Student_Name']}  ({student['Student_ID']})")
    print(f"Course    {evidence['course_id']}  Section {evidence['section_id']}  "
          f"Term {evidence['term']}")
    _rule()

    print(f"{_found_tag(enrollment['found'])}  ENROLLMENT")
    if enrollment["found"]:
        print(f"          Takes record found. Grade on file: "
              f"{enrollment['record'].get('Grade') or '(in progress / blank)'}")
    else:
        print("          No matching Takes record found for this course/section/term.")
    print()

    print(f"{_status_tag(window['satisfied'])}  SUBMISSION WINDOW")
    print(f"          Missed exam: {window['missed_exam_date']}   "
          f"Filed: {window['request_date']}   "
          f"Working days elapsed: {window['working_days_elapsed']} "
          f"(limit {window['limit_working_days']})")
    print()

    print(f"{_status_tag(proof['provided'])}  PROOF PROVIDED")
    print(f"          {proof['raw_value'] or '(none provided)'}")
    if proof.get("file_attached"):
        source_label = "local test file" if proof.get("file_source") == "local" else "fetched from Proof_File_URL"
        count = proof.get("file_count", 1)
        plural = "s" if count != 1 else ""
        print(f"          {count} file{plural} attached and sent to Gemini ({source_label})")
    elif proof.get("file_url"):
        print(f"          Uploaded file: {proof['file_url']}  (URL present but could not be fetched)")
    print()

    print(f"{_status_tag(exam_type['excluded'] if exam_type['excluded'] is None else not exam_type['excluded'])}  EXAM TYPE")
    if exam_type["excluded_values_confirmed"]:
        print(f"          Exam_Type: {exam_type['value']}   Excluded: {exam_type['excluded']}")
    else:
        print(f"          Exam_Type: {exam_type['value']}   "
              f"(excluded-type list not yet confirmed -- see knowledge base TODO)")
    _rule()

    status_note = ""
    if result["gemini_status"] != "ok":
        status_note = f"  (gemini_status={result['gemini_status']}: {result['gemini_error']})"
    print(f"{_rec_tag(result['recommendation'])}{status_note}")
    print()
    print("Reasoning:")
    print(_wrap(result["reasoning"], indent="  "))
    print()
    print("Per-check explanation:")
    for label, key in [
        ("Enrollment", "enrollment"),
        ("Submission window", "submission_window"),
        ("Proof", "proof"),
        ("Reason validity", "reason_validity"),
        ("Exam type", "exam_type"),
    ]:
        print(f"  {label}:")
        print(_wrap(gemini_explanations.get(key), indent="    "))
    _rule("=")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m app.agent <request_id>")
        sys.exit(1)
    request_id = sys.argv[1]

    try:
        result = evaluate_incomplete_exam_request_workflow(request_id)
    except AgentError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    _print_report(result)
    print()
    print("Full JSON result:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()