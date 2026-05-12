# Separated from the tool itself
# If Google changes their auth, only this file changes

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from core.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def get_drive_client():
    if settings.google_credentials_json:
        # Load from environment variable (Best for Deployment)
        creds_dict = json.loads(settings.google_credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES,
        )
    else:
        # Fallback to local file (Best for Development)
        credentials = service_account.Credentials.from_service_account_file(
            settings.google_credentials_path,
            scopes=SCOPES,
        )
    return build("drive", "v3", credentials=credentials)