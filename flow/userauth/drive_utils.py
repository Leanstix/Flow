import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from flow import settings

# Google Drive credentials file
GOOGLE_CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, 'path_to_service_account.json')
GOOGLE_DRIVE_FOLDER_ID = "your_drive_folder_id"  # Replace with your shared folder ID

def upload_to_google_drive(file_path, file_name):
    """
    Uploads a file to Google Drive and returns the file's public URL.
    """
    credentials = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE)
    drive_service = build('drive', 'v3', credentials=credentials)
    
    file_metadata = {
        'name': file_name,
        'parents': [GOOGLE_DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='image/jpeg')  # Update mimetype based on file type

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    # Make the file publicly accessible
    drive_service.permissions().create(
        fileId=uploaded_file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    # Return the file's public URL
    file_url = f"https://drive.google.com/uc?id={uploaded_file['id']}&export=download"
    return file_url
