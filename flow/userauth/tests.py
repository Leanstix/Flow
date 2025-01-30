from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from .drive_utils import upload_file_to_drive  # Import your function

class DriveUploadTestCase(TestCase):
    def test_upload_file_to_drive(self):
        """
        Test that the `upload_file_to_drive` function works correctly.
        """
        # Create a dummy file for testing
        dummy_file = SimpleUploadedFile(
            "test.jpg",  # File name
            b"file_content",  # File content (bytes)
            content_type="image/jpeg"  # MIME type
        )

        try:
            # Call the upload function
            drive_url = upload_file_to_drive(dummy_file, "test.jpg")
            print(f"File uploaded successfully: {drive_url}")

            # Assert that the function returns a valid URL
            self.assertIsNotNone(drive_url)
            self.assertTrue(drive_url.startswith("https://drive.google.com/uc?id="))
        except Exception as e:
            self.fail(f"Error uploading file: {str(e)}")