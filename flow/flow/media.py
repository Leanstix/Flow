import mimetypes
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.exceptions import ValidationError

try:
    import cloudinary.uploader
    from cloudinary.utils import cloudinary_url
except ImportError:  # pragma: no cover - dependency is installed in production
    cloudinary = None
    cloudinary_url = None


IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
VIDEO_TYPES = {'video/mp4', 'video/quicktime', 'video/webm', 'video/x-m4v'}
AUDIO_TYPES = {
    'audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/aac', 'audio/ogg',
    'audio/wav', 'audio/x-wav', 'audio/webm',
}
DOCUMENT_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv', 'application/zip',
}


def upload_mime_type(upload):
    value = (getattr(upload, 'content_type', '') or '').lower().strip()
    if value:
        return value
    guessed, _ = mimetypes.guess_type(getattr(upload, 'name', ''))
    return guessed or 'application/octet-stream'


def validate_upload(upload, *, allowed_types, max_bytes, label='File'):
    mime_type = upload_mime_type(upload)
    if mime_type not in allowed_types:
        allowed = ', '.join(sorted(allowed_types))
        raise ValidationError({"media": f'{label} type {mime_type} is not supported. Allowed: {allowed}.'})
    if getattr(upload, 'size', 0) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ValidationError({"media": f'{label} must be {limit_mb} MB or smaller.'})
    return mime_type


def _cloudinary_enabled():
    return bool(
        getattr(settings, 'CLOUDINARY_URL', None)
        or (
            getattr(settings, 'CLOUDINARY_CLOUD_NAME', None)
            and getattr(settings, 'CLOUDINARY_API_KEY', None)
            and getattr(settings, 'CLOUDINARY_API_SECRET', None)
        )
    )


def _safe_name(name):
    stem = Path(name or 'upload').stem[:60]
    suffix = Path(name or '').suffix.lower()[:10]
    return f'{stem}-{uuid.uuid4().hex[:12]}{suffix}'


def store_upload(
    upload,
    *,
    folder,
    kind,
    trim_start_seconds=0,
    trim_end_seconds=None,
    declared_duration_seconds=None,
):
    """Persist an upload and return normalized delivery metadata.

    Cloudinary URLs deliberately cap feed media resolution and use automatic
    quality/format selection. The original upload is never exposed to clients.
    """

    mime_type = upload_mime_type(upload)
    trim_start = max(float(trim_start_seconds or 0), 0)
    trim_end = float(trim_end_seconds) if trim_end_seconds not in (None, '') else None
    declared_duration = float(declared_duration_seconds) if declared_duration_seconds not in (None, '') else None

    if trim_end is not None and trim_end <= trim_start:
        raise ValidationError({'trim_end_seconds': 'Trim end must be greater than trim start.'})

    if _cloudinary_enabled() and cloudinary_url:
        resource_type = 'video' if kind in {'video', 'audio'} else 'image' if kind == 'image' else 'raw'
        result = cloudinary.uploader.upload(
            upload,
            folder=folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )
        public_id = result.get('public_id', '')
        original_duration = result.get('duration')
        effective_duration = (
            trim_end - trim_start
            if trim_end is not None
            else float(original_duration or declared_duration or 0)
        )

        if kind == 'image':
            url, _ = cloudinary_url(
                public_id,
                resource_type='image',
                secure=True,
                width=1440,
                crop='limit',
                quality='auto:eco',
                fetch_format='auto',
            )
            thumbnail_url, _ = cloudinary_url(
                public_id,
                resource_type='image',
                secure=True,
                width=640,
                height=640,
                crop='limit',
                quality='auto:eco',
                fetch_format='auto',
            )
        elif kind == 'video':
            transform = {
                'resource_type': 'video',
                'secure': True,
                'width': 720,
                'crop': 'limit',
                'video_codec': 'auto',
                'quality': 'auto:eco',
                'fetch_format': 'auto',
            }
            if trim_start:
                transform['start_offset'] = trim_start
            if trim_end is not None:
                transform['end_offset'] = trim_end
            url, _ = cloudinary_url(public_id, **transform)
            thumbnail_url, _ = cloudinary_url(
                public_id,
                resource_type='video',
                secure=True,
                format='jpg',
                start_offset=trim_start or 0,
                width=720,
                crop='limit',
                quality='auto:eco',
            )
        elif kind == 'audio':
            transform = {'resource_type': 'video', 'secure': True, 'audio_codec': 'aac'}
            if trim_start:
                transform['start_offset'] = trim_start
            if trim_end is not None:
                transform['end_offset'] = trim_end
            url, _ = cloudinary_url(public_id, **transform)
            thumbnail_url = ''
        else:
            url = result.get('secure_url') or result.get('url')
            thumbnail_url = ''

        return {
            'url': url,
            'thumbnail_url': thumbnail_url,
            'public_id': public_id,
            'mime_type': mime_type,
            'file_name': getattr(upload, 'name', ''),
            'size_bytes': int(result.get('bytes') or getattr(upload, 'size', 0) or 0),
            'duration_seconds': round(effective_duration, 3) if effective_duration else None,
            'width': result.get('width'),
            'height': result.get('height'),
            'trim_start_seconds': trim_start,
            'trim_end_seconds': trim_end,
        }

    storage_name = default_storage.save(
        os.path.join(folder, _safe_name(getattr(upload, 'name', 'upload'))),
        upload,
    )
    return {
        'url': default_storage.url(storage_name),
        'thumbnail_url': '',
        'public_id': storage_name,
        'mime_type': mime_type,
        'file_name': getattr(upload, 'name', ''),
        'size_bytes': int(getattr(upload, 'size', 0) or 0),
        'duration_seconds': round(
            (trim_end - trim_start) if trim_end is not None else float(declared_duration or 0),
            3,
        ) or None,
        'width': None,
        'height': None,
        'trim_start_seconds': trim_start,
        'trim_end_seconds': trim_end,
    }
