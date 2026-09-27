# Proof documents (local test-only)

Put proof documents here, named after their Request_ID. The agent picks them up
automatically and sends them to Gemini as real attachments. You don't need Supabase
Storage, a database column, or a network fetch.

## Naming convention

Single document:

    <Request_ID>.<extension>

Multiple documents for the same request:

    <Request_ID>-<label>.<extension>

Examples (currently in this folder):

    STUD_INCRQ_INC2_000008-medical.pdf
    STUD_INCRQ_INC2_000008-police.pdf
    STUD_INCRQ_INC2_000009-flight.pdf
    STUD_INCRQ_INC2_000009-statement.pdf

All matching files for a request are attached together.

Supported extensions: .pdf, .png, .jpg, .jpeg, .webp (max 10 MB per file). Files that
are unreadable, too large, or have another extension are skipped with a warning.

## How it's used

This is a TEST-ONLY convenience for local development. Local files are checked BEFORE
`Incomplete_Exam.Proof_File_URL` (see `app/tools/proof_file_tools.py`). If any matching
local file exists, it's used, and the database URL is only a fallback (single file
only). Real students can't put files into this codebase. The folder is here so you can
test how the agent reads documents before real file storage is set up.

If no document is found, the evidence reports `file_attached: false`, and Gemini
treats the proof as unverified (normally `MANUAL_REVIEW`).
