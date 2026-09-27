"""Gemini is the decision-making layer of this agent:
Python only collects and computes verified evidence; it does NOT combine that evidence
into a final APPROVE/REJECT/MANUAL_REVIEW recommendation itself. Gemini receives the
full evidence package plus explicit decision rules and produces the recommendation and
an explanation for each check.
"""

import json
from typing import TypedDict

from google import genai
from google.genai import types
from pydantic import BaseModel

from app import config


class Attachment(TypedDict):
    """One uploaded document to hand to Gemini alongside the text evidence.
    TEST-ONLY: this is for the standalone test page's one-off manual attachment
    feature, not a persisted, real proof-upload pipeline -- nothing here is saved
    anywhere. See app/services/gemini.py's get_gemini_decision docstring.
    """
    filename: str
    mime_type: str
    data: bytes

_UNAVAILABLE_CHECKS = {
    "enrollment": "Not evaluated -- Gemini unavailable.",
    "submission_window": "Not evaluated -- Gemini unavailable.",
    "proof": "Not evaluated -- Gemini unavailable.",
    "reason_validity": "Not evaluated -- Gemini unavailable.",
    "exam_type": "Not evaluated -- Gemini unavailable.",
}

_DECISION_RULES = """
You are evaluating an Incomplete Exam request for a university student, using ONLY
the evidence provided below. Do not invent, assume, or infer any fact that is not
present in the evidence.

IMPORTANT -- proof must be an actual reviewed document, not just a text claim:
The evidence includes checks.proof.file_attached (true/false). A text description in
Proof (e.g. "police report submitted") is NOT itself verifiable evidence -- it is only
what the student or staff typed. Only treat proof as actually verified if
file_attached is true AND the attached document was reviewed below and found
genuinely consistent with the stated reason. If file_attached is false, the proof
claim is unverified, no matter how plausible the text sounds.

Recommend APPROVE only if all of the following hold:
- The student was verifiably enrolled in the referenced course/section/term
- The request was filed within the allowed submission window
- file_attached is true, and the attached document was reviewed and found genuinely
  consistent with the stated reason and an acceptable proof category
- The stated reason is clearly NOT one of the explicitly invalid categories listed
- The exam type is not a confirmed-excluded type

Recommend REJECT if any of the above is verifiably and clearly failed -- for example,
the request was filed after the submission window, the stated reason clearly and
unambiguously matches an explicitly invalid category (misreading the exam schedule,
personal travel, or a standard job obligation), the exam type is confirmed excluded,
or an attached document is inconsistent with the claim or explicitly states it is not
a real record (e.g. sample or test data).

Recommend MANUAL_REVIEW if anything needed to decide is missing, unclear, ambiguous,
or could not be verified -- including: no enrollment record found; file_attached is
false, meaning a reason was stated but no actual document exists to verify it
against; a borderline or ambiguous stated reason; or the excluded-exam-type list not
yet being confirmed. Never guess when evidence is incomplete or unclear;
MANUAL_REVIEW exists specifically for that situation.
"""

_ATTACHMENT_INSTRUCTIONS = """
One or more supporting documents have been attached below (after the evidence). Look
at them directly as part of your proof and reason-validity assessment -- for example,
whether a document appears consistent with the stated reason (a medical/police
document for an accident claim, a travel document for a travel claim), and whether it
looks like a genuine document of that type. You cannot verify an issuing
authority's authenticity with certainty from an image or PDF alone -- if the
attachment is illegible, inconclusive, or you are not confident it is genuine, say so
plainly in your proof/reason_validity explanations rather than treating it as
confirmed proof. A file being attached is NECESSARY but not SUFFICIENT for APPROVE --
do not upgrade the recommendation to APPROVE purely because a file was attached; the
same MANUAL_REVIEW and REJECT rules above still apply based on what the document
actually shows.
"""


class _IncompleteExamDecision(BaseModel):
    recommendation: str
    reasoning: str
    enrollment_explanation: str
    submission_window_explanation: str
    proof_explanation: str
    reason_validity_explanation: str
    exam_type_explanation: str


def get_gemini_decision(evidence_package: dict, attachments: list[Attachment] | None = None) -> dict:
    """attachments is TEST-ONLY (see the Attachment docstring) -- normal calls from
    app/agent.py never pass this; it exists for the standalone test page's one-off
    "attach a file and see what Gemini makes of it" feature."""
    if not config.GEMINI_API_KEY:
        return {
            "recommendation": "MANUAL_REVIEW",
            "reasoning": "Gemini API key is not configured, so no automated "
            "recommendation could be produced.",
            "checks": dict(_UNAVAILABLE_CHECKS),
            "status": "unavailable",
            "error": "GEMINI_API_KEY not configured",
        }

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    rules = _DECISION_RULES + (_ATTACHMENT_INSTRUCTIONS if attachments else "")
    prompt = rules + "\n\nEvidence:\n" + json.dumps(evidence_package, indent=2, default=str)

    contents: list = [prompt]
    for att in attachments or []:
        contents.append(types.Part.from_bytes(data=att["data"], mime_type=att["mime_type"]))

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_IncompleteExamDecision,
            ),
        )
        decision: _IncompleteExamDecision | None = getattr(response, "parsed", None)
        if decision is None:
            return {
                "recommendation": "MANUAL_REVIEW",
                "reasoning": "Gemini's structured response could not be parsed.",
                "checks": dict(_UNAVAILABLE_CHECKS),
                "status": "error",
                "error": "response.parsed was None",
            }
    except Exception as exc:  # noqa: BLE001 -- any Gemini failure falls back to MANUAL_REVIEW
        return {
            "recommendation": "MANUAL_REVIEW",
            "reasoning": f"Gemini could not be reached or returned an unusable "
            f"response: {exc}",
            "checks": dict(_UNAVAILABLE_CHECKS),
            "status": "error",
            "error": str(exc),
        }

    return {
        "recommendation": decision.recommendation,
        "reasoning": decision.reasoning,
        "checks": {
            "enrollment": decision.enrollment_explanation,
            "submission_window": decision.submission_window_explanation,
            "proof": decision.proof_explanation,
            "reason_validity": decision.reason_validity_explanation,
            "exam_type": decision.exam_type_explanation,
        },
        "status": "ok",
        "error": None,
    }