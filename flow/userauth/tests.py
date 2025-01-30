from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from .drive_utils import upload_file_to_drive  # Import your function

User = get_user_model()

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

class UserProfileUpdateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="leanstixx@gmail.com",
            university_id="231472",
            password="Ka1,@yada24.@sa"
        )
        self.client.force_authenticate(user=self.user)

    def test_profile_picture_update(self):
        # Create a dummy file for testing
        dummy_file = SimpleUploadedFile(
            "test.jpg",  # File name
            b"file_content",  # File content (bytes)
            content_type="image/jpeg"  # MIME type
        )

        # Update profile with the dummy file
        response = self.client.patch(
            "/api/userauth/profile/update/",
            {"profile_picture": dummy_file},
            format="multipart"
        )

        # Check the response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["profile_picture"].startswith("https://drive.google.com/uc?id="))