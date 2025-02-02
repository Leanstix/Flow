from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import json
import os
from io import BytesIO

SCOPES = ['https://www.googleapis.com/auth/drive.file']
PARENT_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_PARENT_FOLDER_ID')

# Parse the JSON string
credentials_info = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
if not credentials_info:
    raise ValueError("Environment variable 'GOOGLE_DRIVE_CREDENTIALS' is not set.")

try:
    SERVICE_ACCOUNT_INFO = json.loads(credentials_info)
except json.JSONDecodeError:
    raise ValueError("Invalid JSON format in 'GOOGLE_DRIVE_CREDENTIALS'.")

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES
)

drive_service = build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(file_obj, file_name):
    file_metadata = {'name': file_name, 'parents': [PARENT_FOLDER_ID]}
    mimetype = file_obj.content_type if hasattr(file_obj, 'content_type') else 'application/octet-stream'
    
    # Ensure the file object is in a file-like state
    if hasattr(file_obj, 'read'):
        file_stream = file_obj
    else:
        file_stream = BytesIO(file_obj.encode() if isinstance(file_obj, str) else file_obj)

    media = MediaIoBaseUpload(file_stream, mimetype=mimetype, resumable=True)

    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    file_id = file.get('id')
    return f"https://drive.google.com/uc?id={file_id}&authuser=0"
    