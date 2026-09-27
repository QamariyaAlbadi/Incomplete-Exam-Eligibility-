"""Provides proof document(s) to hand to Gemini as actual attachments, not just a
text description. Two sources, checked in order:

1. Local file(s) in app/knowledge_base/proof_documents/, named <Request_ID>.<ext> for
   a single document, or <Request_ID>-<label>.<ext> for multiple (e.g.
   STUD_INCRQ_INC2_000008-medical.pdf and STUD_INCRQ_INC2_000008-police.pdf) --
   TEST-ONLY, see that folder's README. No database, no network, no setup needed.
2. Incomplete_Exam.Proof_File_URL, fetched over HTTP -- for when a real upload
   pipeline eventually exists. Currently supports only a single URL/file; extending
   this to multiple real uploaded files would need a schema change (e.g. a separate
   proof-files table) rather than a single text column.

Both fail soft: a missing or unreadable file returns an empty list/None rather than
raising -- a missing/unfetchable proof document is evidence for Gemini to weigh (see
_DECISION_RULES's MANUAL_REVIEW guidance), not a reason to crash the whole evaluation.
"""

import mimetypes
from pathlib import Path

import requests

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_TIMEOUT_SECONDS = 10

_LOCAL_PROOF_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "proof_documents"


def get_local_proof_files(request_id: str) -> list[dict]:
    """Checks app/knowledge_base/proof_documents/ for ALL files belonging to this
    request -- either a single <request_id>.<ext>, or multiple files named
    <request_id>-<label>.<ext> (e.g. STUD_INCRQ_INC2_000008-medical.pdf and
    STUD_INCRQ_INC2_000008-police.pdf for a request with more than one supporting
    document). Returns a list (possibly empty) of {"filename", "mime_type", "data"}
    dicts. Never raises.
    """
    results = []
    if not _LOCAL_PROOF_DIR.is_dir():
        return results

    for candidate in sorted(_LOCAL_PROOF_DIR.iterdir()):
        if not candidate.is_file() or candidate.suffix.lower() not in _ALLOWED_EXTENSIONS:
            continue
        stem = candidate.stem
        if stem != request_id and not stem.startswith(f"{request_id}-"):
            continue  # belongs to a different request

        try:
            data = candidate.read_bytes()
        except OSError as exc:
            print(f"WARNING: found {candidate} but could not read it: {exc}")
            continue
        if len(data) > _MAX_BYTES:
            print(f"WARNING: {candidate} exceeds {_MAX_BYTES // (1024*1024)} MB; skipping.")
            continue

        mime_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        results.append({"filename": candidate.name, "mime_type": mime_type, "data": data})

    return results


def fetch_proof_file(url: str | None) -> dict | None:
    """Returns {"filename": str, "mime_type": str, "data": bytes} on success, or None
    if there's nothing to fetch or the fetch failed for any reason. Never raises."""
    if not url:
        return None

    try:
        response = requests.get(url, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 -- any network/HTTP failure -> no attachment
        print(f"WARNING: could not fetch Proof_File_URL ({url!r}): {exc}")
        return None

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
    if content_type not in _ALLOWED_MIME_TYPES:
        guessed, _ = mimetypes.guess_type(url)
        if guessed in _ALLOWED_MIME_TYPES:
            content_type = guessed
        else:
            print(f"WARNING: Proof_File_URL ({url!r}) has unsupported type {content_type!r}; skipping attachment.")
            return None

    if len(response.content) > _MAX_BYTES:
        print(f"WARNING: Proof_File_URL ({url!r}) exceeds {_MAX_BYTES // (1024*1024)} MB; skipping attachment.")
        return None

    filename = url.rsplit("/", 1)[-1] or "proof_file"
    return {"filename": filename, "mime_type": content_type, "data": response.content}