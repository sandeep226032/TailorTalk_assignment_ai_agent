# Only knows HOW to search — not how to authenticate
# Not how to format for HTTP — just search logic

from langchain_core.tools import tool
from tools.drive_client import get_drive_client
from core.constants import MIME_LABELS
from core.config import settings

@tool
def drive_search_tool(query: str) -> str:
    """Search Google Drive files using a Drive API q parameter string."""
    service = get_drive_client()
    
    final_query = _build_final_query(query)
    results = service.files().list(
        q=final_query,
        pageSize=15,
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        orderBy="modifiedTime desc",
    ).execute()
    
    return _format_results(results.get("files", []))

def _build_final_query(user_query: str) -> str:
    # Private helper — not exposed as tool
    conditions = [
        user_query,
        "trashed = false",
        # f"'{settings.drive_folder_id}' in parents"
    ]
    return " and ".join(filter(None, conditions))

def _format_results(files: list) -> str:
    if not files:
        return "No files found."
    lines = [f"Found {len(files)} file(s):\n"]
    for i, f in enumerate(files, 1):
        label = MIME_LABELS.get(f.get("mimeType", ""), "Unknown")
        lines.append(f"{i}. {f['name']} ({label}) — {f.get('webViewLink', 'no link')}")
    return "\n".join(lines)