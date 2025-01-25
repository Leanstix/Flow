from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_INFO = json.loads(os.environ.get('GOOGLE_DRIVE_CREDENTIALS'))

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES)

drive_service = build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(file_obj, file_name):
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_obj, mimetype=file_obj.content_type, resumable=True)

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = file.get('id')
    return f"https://drive.google.com/uc?id={file_id}&export=download"
