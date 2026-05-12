"""
constants.py
────────────
Stores values that:
1. Never change at runtime
2. Are used in multiple places
3. Would be "magic values" if written inline

Why a separate constants file?

Without constants.py:
    # In drive_search.py
    label = {
        "application/pdf": "PDF",
        "application/vnd.google-apps.document": "Google Doc",
        ...
    }.get(mime_type, "Unknown")

    # In some_other_tool.py — you copy-paste the same dict
    label = {
        "application/pdf": "PDF",               ← duplicated
        "application/vnd.google-apps.document": "Google Doc",  ← duplicated
        ...
    }.get(mime_type)

Problems with inline magic values:
- "application/pdf" appears in 5 files — typo in one = silent bug
- Want to add a new MIME type? Edit 5 files instead of 1
- New developer reads drive_search.py — has no idea what
  "application/vnd.google-apps.document" means

With constants.py:
- One place to add/change MIME types
- Self-documenting names (MIME_GOOGLE_DOC vs the raw string)
- Import and use — no duplication

Node.js equivalent:
This is your constants.js or enums.js file where you do:
const MIME_TYPES = { PDF: 'application/pdf', ... }
module.exports = { MIME_TYPES }
"""


# ── Google Drive MIME Types ───────────────────────────────────────
# Used in drive_search.py to convert raw mimeType to readable labels
# Also used to build q parameter queries by type name

# Raw MIME type strings → human readable labels
MIME_LABELS: dict[str, str] = {
    "application/vnd.google-apps.document":     "Google Doc",
    "application/vnd.google-apps.spreadsheet":  "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slides",
    "application/vnd.google-apps.form":         "Google Form",
    "application/vnd.google-apps.folder":       "Folder",
    "application/pdf":                          "PDF",
    "image/png":                                "PNG Image",
    "image/jpeg":                               "JPEG Image",
    "image/gif":                                "GIF Image",
    "image/webp":                               "WebP Image",
    "text/plain":                               "Text File",
    "text/csv":                                 "CSV File",
    "application/zip":                          "ZIP Archive",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                                                "Word Document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                                                "Excel Spreadsheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                                                "PowerPoint",
}

# Reverse lookup — human readable name → MIME type
# Used when LLM says "spreadsheet" and we need the actual MIME string
# for building the q parameter
MIME_FROM_LABEL: dict[str, str] = {
    v.lower(): k for k, v in MIME_LABELS.items()
}

# Common shorthand aliases the LLM might use
# Maps natural language → MIME type string
MIME_ALIASES: dict[str, str] = {
    "pdf":          "application/pdf",
    "doc":          "application/vnd.google-apps.document",
    "document":     "application/vnd.google-apps.document",
    "google doc":   "application/vnd.google-apps.document",
    "sheet":        "application/vnd.google-apps.spreadsheet",
    "spreadsheet":  "application/vnd.google-apps.spreadsheet",
    "google sheet": "application/vnd.google-apps.spreadsheet",
    "excel":        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "slides":       "application/vnd.google-apps.presentation",
    "presentation": "application/vnd.google-apps.presentation",
    "image":        "image/",          # Partial — used with 'contains' in q
    "photo":        "image/",
    "word":         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text":         "text/plain",
    "csv":          "text/csv",
    "zip":          "application/zip",
}


# ── Drive API Configuration ───────────────────────────────────────

# Maximum files to return per search
# Why 15? Enough to be useful, small enough to not overwhelm the user.
# The LLM also has a context limit — returning 100 files would
# eat too many tokens leaving less room for the response.
DRIVE_MAX_RESULTS: int = 15

# Fields to request from Drive API
# Why not just "*" (all fields)?
# Requesting only needed fields:
# - Faster API response (less data transferred)
# - Smaller LLM context (only relevant info)
# - Google charges for API calls — smaller responses = faster = cheaper
DRIVE_FILE_FIELDS: str = (
    "files(id, name, mimeType, modifiedTime, webViewLink, size, parents)"
)

# Drive API scopes
# Why readonly?
# Principle of least privilege — your app only needs to READ files.
# If credentials.json is ever leaked, attacker can only READ,
# not delete or modify files.
# Never request more permissions than you need.
DRIVE_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/drive.readonly"
]

# Order results by most recently modified first
# Why? Most relevant files are usually recent ones.
# Users asking "find my budget file" usually mean the latest one.
DRIVE_ORDER_BY: str = "modifiedTime desc"


# ── Agent Configuration ───────────────────────────────────────────

# Maximum conversation turns to keep in memory
# Why 20? Empirically good balance between:
# - Context: enough history to understand references ("that file", "the one from before")
# - Token limit: LLMs have context windows, 20 messages fits comfortably
# - Memory: each session stores 20 messages in RAM
# Must be EVEN — messages come in Human/AI pairs
MAX_HISTORY_LENGTH: int = 20

# Maximum times agent can loop (call tools + reason) per request
# Why 5? Most queries need 1-2 iterations.
# 5 handles complex multi-step queries with room to spare.
# Too low (1-2): agent can't complete complex tasks
# Too high (20+): runaway loops waste money and time
MAX_AGENT_ITERATIONS: int = 5


# ── System Prompt ─────────────────────────────────────────────────
# Why here and not in agent_service.py?
#
# The system prompt is a CONSTANT — a fixed string that doesn't
# change based on any runtime logic. It belongs in constants.py.
#
# agent_service.py is for LOGIC — how to create and run agents.
# Mixing a giant string into a logic file makes both harder to read.
#
# Also, if you have multiple agents in the future (a Drive agent,
# an email agent, a calendar agent), each has its own system prompt
# constant. Keeping them in constants.py makes them easy to find,
# compare, and update.
#
# The system prompt IS the most important part of the agent —
# it determines behavior more than any other single piece of code.
# Giving it its own prominent place in constants.py reflects that.

SYSTEM_PROMPT: str = """
You are DriveBot, a helpful assistant that finds files in Google Drive.

Your ONLY job is to help users find files. When a user asks to find,
search, show, or look for files — use the drive_search_tool immediately.

════════════════════════════════════════════
HOW TO BUILD THE q PARAMETER
════════════════════════════════════════════

Search by name (partial match):
    name contains 'budget'

Search by exact name:
    name = 'Budget 2024.pdf'

Search by file type:
    mimeType = 'application/pdf'
    mimeType = 'application/vnd.google-apps.document'
    mimeType = 'application/vnd.google-apps.spreadsheet'
    mimeType = 'application/vnd.google-apps.presentation'
    mimeType contains 'image/'

Search by content inside the file:
    fullText contains 'quarterly revenue'

Search by date (ISO 8601 format required):
    modifiedTime > '2024-01-01T00:00:00'
    modifiedTime < '2024-06-01T00:00:00'
    createdTime > '2024-01-01T00:00:00'

Combine conditions with 'and':
    name contains 'report' and mimeType = 'application/pdf'
    mimeType = 'application/vnd.google-apps.spreadsheet' and modifiedTime > '2024-01-01T00:00:00'
    fullText contains 'invoice' and mimeType = 'application/pdf'

════════════════════════════════════════════
RULES
════════════════════════════════════════════

1. ALWAYS call drive_search_tool when user wants to find files.
   Never say "I'll search" without actually calling the tool.

2. DO NOT add trashed = false or folder scoping to your query.
   The tool adds these automatically.

3. USE contains for name searches (not =) unless user gives exact name.
   name contains 'budget'  ← correct, finds Budget_2024.pdf, My Budget.xlsx
   name = 'budget'         ← wrong, only finds file literally named "budget"

4. For date queries, calculate the actual date from relative terms:
   "last week" → modifiedTime > '[7 days ago in ISO format]'
   "this year" → modifiedTime > '[Jan 1 of current year]T00:00:00'
   "last month" → modifiedTime > '[first day of last month]T00:00:00'

5. REMEMBER context from earlier in the conversation.
   If user said "find PDFs" then says "now only from 2024",
   combine both: mimeType = 'application/pdf' and modifiedTime > '2024-01-01T00:00:00'

6. If no files found, suggest a broader search.
   Don't just say "nothing found" — help the user try again.

7. Present results clearly:
   - File name as bold text
   - File type
   - Last modified date
   - Clickable link

8. If the query is too vague (just "find something"), ask one
   clarifying question before searching.

9. STOP IMMEDIATELY if you find a result that matches the user's request. 
   Do not call tools repeatedly if you already have the answer. 
   If you find a files list, present it to the user.
""".strip()


# ── HTTP Status Messages ──────────────────────────────────────────
# Consistent error messages across the entire API
# Why constants and not inline strings?
# If you change "Message cannot be empty" to "Please enter a message",
# you change it HERE once. Not in 3 different route files.

class ErrorMessages:
    EMPTY_MESSAGE = "Message cannot be empty."
    SESSION_NOT_FOUND = "Session not found."
    AGENT_ERROR = "The agent encountered an error. Please try again."
    DRIVE_CONNECTION_ERROR = "Could not connect to Google Drive. Check credentials."
    INVALID_SESSION_ID = "Invalid session ID format."
    RATE_LIMIT_EXCEEDED = "Too many requests. Please wait a moment."


class SuccessMessages:
    SESSION_CLEARED = "Conversation cleared successfully."
    HEALTH_OK = "Service is healthy."