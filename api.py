"""Minimal local-only HTTP wrapper around the agent, for the standalone test page.

This is NOT part of the agent's own architecture, and NOT the real FastAPI backend
the project's Section 4.1 tech stack describes for the whole system -- it's a small,
temporary bridge so a browser can call this one agent while testing it in isolation,
before it's wired into anything real.

Run with:
    pip install fastapi uvicorn
    uvicorn api:app --reload --port 8000

Then open test_page.html in a browser (as a local file is fine).
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.agent import evaluate_incomplete_exam_request_workflow
from app.exceptions import AgentError

_ALLOWED_ATTACHMENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB, generous for a test tool

app = FastAPI(title="Agent 5 test API (local only)")

# Wide open CORS is fine here ONLY because this is a local dev tool never meant to be
# deployed anywhere real -- do not carry this setting into the actual project backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/evaluate/{request_id}")
def evaluate(request_id: str):
    try:
        return evaluate_incomplete_exam_request_workflow(request_id)
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/evaluate-with-attachments/{request_id}")
async def evaluate_with_attachments(request_id: str, files: list[UploadFile] = File(...)):
    """TEST-ONLY: lets the standalone test page attach one or more documents for a
    single evaluation. Nothing here is saved anywhere -- the files exist only in
    memory for the duration of this one request, then are discarded.
    """
    attachments = []
    for f in files:
        if f.content_type not in _ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{f.content_type}' for {f.filename!r}. "
                f"Allowed: {', '.join(sorted(_ALLOWED_ATTACHMENT_TYPES))}.",
            )
        data = await f.read()
        if len(data) > _MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"{f.filename!r} is too large (max {_MAX_ATTACHMENT_BYTES // (1024*1024)} MB).",
            )
        attachments.append({"filename": f.filename, "mime_type": f.content_type, "data": data})

    try:
        return evaluate_incomplete_exam_request_workflow(request_id, attachments=attachments)
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
