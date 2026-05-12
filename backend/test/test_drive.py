"""
Run this to verify service account can see your folder.
cd backend
python test_drive.py
"""

import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "secrets/credentials.json")

def test_connection():
    print(f"Testing with folder ID: {FOLDER_ID}")
    print(f"Using credentials: {CREDS_PATH}")

    # Step 1: Build service
    try:
        credentials = service_account.Credentials.from_service_account_file(
            CREDS_PATH,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        service = build("drive", "v3", credentials=credentials)
        print("✅ Credentials loaded successfully")
    except Exception as e:
        print(f"❌ Credentials failed: {e}")
        return

    # Step 2: Test folder access directly
    try:
        folder = service.files().get(
            fileId=FOLDER_ID,
            fields="id, name, mimeType"
        ).execute()
        print(f"✅ Folder found: '{folder['name']}'")
    except Exception as e:
        print(f"❌ Cannot access folder: {e}")
        print("   → Folder ID wrong OR service account not shared on folder")
        return

    # Step 3: List files inside folder
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed = false",
            fields="files(id, name, mimeType)",
            pageSize=20,
        ).execute()

        files = results.get("files", [])

        if not files:
            print("⚠️  Folder accessible but EMPTY")
            print("   → Files not copied into this folder yet")
        else:
            print(f"✅ Found {len(files)} files:")
            for f in files:
                print(f"   - {f['name']} ({f['mimeType']})")

    except Exception as e:
        print(f"❌ Cannot list files: {e}")

if __name__ == "__main__":
    test_connection()