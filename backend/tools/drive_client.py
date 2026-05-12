# Separated from the tool itself
# If Google changes their auth, only this file changes

from google.oauth2 import service_account
from googleapiclient.discovery import build
from core.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def get_drive_client():
    credentials = service_account.Credentials.from_service_account_file(
        settings.google_credentials_path,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=credentials)