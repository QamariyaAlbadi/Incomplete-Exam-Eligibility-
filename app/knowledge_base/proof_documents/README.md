# Proof documents (local test-only)

Drop a proof document here named after its Request_ID, and the agent will
automatically pick it up and send it to Gemini as a real attachment -- no Supabase
Storage, no database column, no network fetch needed.

Naming convention: `<Request_ID>.<extension>`

Examples:
    STUD_INCRQ_INC2_000008.pdf
    STUD_INCRQ_INC2_000009.jpg

Supported extensions: .pdf, .png, .jpg, .jpeg, .webp

This is a TEST-ONLY convenience for local development. It is checked BEFORE
Incomplete_Exam.Proof_File_URL (see app/tools/proof_file_tools.py) -- if a matching
local file exists, it's used; the database URL is only consulted as a fallback. Real
students obviously can't put files directly into this codebase -- this exists purely
so you can test the agent's document-reading behavior without setting up real file
storage first.
