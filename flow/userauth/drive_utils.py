import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

def upload_to_google_drive(file_path, file_name):
    """Upload a file to Google Drive and return the shared link."""
    try:
        # Load credentials from the environment variable
        credentials_info = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
        credentials = Credentials.from_service_account_info(credentials_info)

        # Build the Google Drive API service
        service = build('drive', 'v3', credentials=credentials)

        # Define file metadata and upload
        file_metadata = {'name': file_name}
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        # Make the file publicly accessible
        file_id = file.get('id')
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()

        # Generate the shared link
        shared_link = f"https://drive.google.com/uc?id={file_id}&export=download"
        return shared_link

    except Exception as e:
        print(f"Error uploading file to Google Drive: {e}")
        return None
