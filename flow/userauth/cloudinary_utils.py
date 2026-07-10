from urllib.parse import unquote, urlparse

import cloudinary
import cloudinary.uploader
from django.conf import settings


def _cloudinary_credentials():
    if settings.CLOUDINARY_URL:
        parsed = urlparse(settings.CLOUDINARY_URL)
        if parsed.scheme != 'cloudinary':
            raise ValueError("CLOUDINARY_URL must start with 'cloudinary://'.")

        credentials = {
            'cloud_name': parsed.hostname,
            'api_key': unquote(parsed.username or ''),
            'api_secret': unquote(parsed.password or ''),
        }
    else:
        credentials = {
            'cloud_name': settings.CLOUDINARY_CLOUD_NAME,
            'api_key': settings.CLOUDINARY_API_KEY,
            'api_secret': settings.CLOUDINARY_API_SECRET,
        }

    missing = [name for name, value in credentials.items() if not value]
    if missing:
        raise ValueError(
            'Cloudinary is not configured. Set CLOUDINARY_URL or all of '
            'CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET.'
        )

    return credentials


def upload_profile_picture(file_obj):
    cloudinary.config(**_cloudinary_credentials(), secure=True)
    result = cloudinary.uploader.upload(
        file_obj,
        folder=settings.CLOUDINARY_PROFILE_FOLDER,
        resource_type='image',
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )

    secure_url = result.get('secure_url')
    if not secure_url:
        raise ValueError('Cloudinary did not return a secure URL for the uploaded image.')

    return secure_url
