from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import json
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_INFO = json.loads(os.environ.get('GOOGLE_DRIVE_CREDENTIALS'))

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES)

drive_service = build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(file_obj, file_name):
    file_metadata = {'name': file_name}
    if hasattr(file_obj, 'content_type'):  # File object from request.FILES
        mimetype = file_obj.content_type
        file_stream = file_obj
    else:  # Convert string or bytes data to file-like object
        mimetype = 'application/octet-stream'
        file_stream = BytesIO(file_obj.encode() if isinstance(file_obj, str) else file_obj)

media = MediaIoBaseUpload(file_stream, mimetype=mimetype, resumable=True)

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = file.get('id')
    return f"https://drive.google.com/uc?id={file_id}&export=download"
