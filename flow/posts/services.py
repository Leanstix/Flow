import json
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from flow.media import IMAGE_TYPES, VIDEO_TYPES, store_upload, validate_upload
from notifications.models import Notification
from notifications.services import create_notification

from .models import Hashtag, PostMedia

User = get_user_model()
HASHTAG_PATTERN = re.compile(r'(?<![\w#])#([A-Za-z0-9_]{1,80})')
MENTION_PATTERN = re.compile(r'(?<![\w@])@([A-Za-z0-9_.]{1,80})')
MAX_POST_MEDIA = 4
MAX_VIDEO_SECONDS = 180


def extract_hashtags(text):
    return list(dict.fromkeys(match.lower() for match in HASHTAG_PATTERN.findall(text or '')))


def extract_mentions(text):
    return list(dict.fromkeys(match.lower() for match in MENTION_PATTERN.findall(text or '')))


def _mentioned_users(text):
    users = []
    for username in extract_mentions(text):
        user = User.objects.filter(user_name__iexact=username, is_active=True).first()
        if user and user.pk not in {item.pk for item in users}:
            users.append(user)
    return users


def sync_post_entities(post, actor):
    hashtags = [Hashtag.objects.get_or_create(name=name)[0] for name in extract_hashtags(post.content)]
    post.hashtags.set(hashtags)
    mentioned = _mentioned_users(post.content)
    post.mentioned_users.set(mentioned)
    actor_name = actor.user_name or actor.email
    for recipient in mentioned:
        create_notification(
            recipient=recipient,
            actor=actor,
            verb=Notification.Verb.MENTION,
            message=f'{actor_name} mentioned you in a post.',
            target_post=post,
        )
    return mentioned


def sync_comment_entities(comment, actor):
    mentioned = _mentioned_users(comment.content)
    comment.mentioned_users.set(mentioned)
    actor_name = actor.user_name or actor.email
    for recipient in mentioned:
        create_notification(
            recipient=recipient,
            actor=actor,
            verb=Notification.Verb.MENTION,
            message=f'{actor_name} mentioned you in a comment.',
            target_post=comment.post,
            target_comment=comment,
        )
    return mentioned


def parse_media_metadata(raw):
    if raw in (None, ''):
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError({'media_metadata': 'Media metadata must be valid JSON.'}) from exc
        if not isinstance(parsed, list):
            raise ValidationError({'media_metadata': 'Media metadata must be a list.'})
        return parsed
    raise ValidationError({'media_metadata': 'Media metadata must be a list.'})


def create_post_media(post, request, metadata=None):
    uploads = list(request.FILES.getlist('media')) if request else []
    if not uploads:
        return []
    if len(uploads) > MAX_POST_MEDIA:
        raise ValidationError({'media': f'A post can contain at most {MAX_POST_MEDIA} media files.'})

    metadata = metadata or []
    videos = [upload for upload in uploads if (getattr(upload, 'content_type', '') or '').lower() in VIDEO_TYPES]
    if len(videos) > 1:
        raise ValidationError({'media': 'A post can contain only one video.'})
    if videos and len(uploads) > 1:
        raise ValidationError({'media': 'Videos cannot be mixed with image galleries in one post.'})

    created = []
    with transaction.atomic():
        for position, upload in enumerate(uploads):
            item_meta = metadata[position] if position < len(metadata) and isinstance(metadata[position], dict) else {}
            mime_type = (getattr(upload, 'content_type', '') or '').lower()
            if mime_type in IMAGE_TYPES:
                validate_upload(upload, allowed_types=IMAGE_TYPES, max_bytes=12 * 1024 * 1024, label='Image')
                stored = store_upload(upload, folder='flow/posts/images', kind='image')
                media_type = PostMedia.MediaType.IMAGE
            elif mime_type in VIDEO_TYPES:
                validate_upload(upload, allowed_types=VIDEO_TYPES, max_bytes=120 * 1024 * 1024, label='Video')
                duration = item_meta.get('duration_seconds')
                trim_start = item_meta.get('trim_start_seconds', 0)
                trim_end = item_meta.get('trim_end_seconds')
                try:
                    effective_duration = (
                        float(trim_end) - float(trim_start or 0)
                        if trim_end not in (None, '')
                        else float(duration or 0)
                    )
                except (TypeError, ValueError) as exc:
                    raise ValidationError({'media_metadata': 'Video duration and trim values must be numbers.'}) from exc
                if effective_duration <= 0:
                    raise ValidationError({'media_metadata': 'A valid video duration is required.'})
                if effective_duration > MAX_VIDEO_SECONDS:
                    raise ValidationError({'media': f'Videos must be {MAX_VIDEO_SECONDS} seconds or shorter after trimming.'})
                stored = store_upload(
                    upload,
                    folder='flow/posts/videos',
                    kind='video',
                    trim_start_seconds=trim_start,
                    trim_end_seconds=trim_end,
                    declared_duration_seconds=duration,
                )
                if stored.get('duration_seconds') and float(stored['duration_seconds']) > MAX_VIDEO_SECONDS:
                    raise ValidationError({'media': f'Videos must be {MAX_VIDEO_SECONDS} seconds or shorter after trimming.'})
                media_type = PostMedia.MediaType.VIDEO
            else:
                raise ValidationError({'media': f'Unsupported post media type: {mime_type or "unknown"}.'})

            created.append(PostMedia.objects.create(
                post=post,
                media_type=media_type,
                url=stored['url'],
                thumbnail_url=stored.get('thumbnail_url') or '',
                public_id=stored.get('public_id') or '',
                file_name=stored.get('file_name') or '',
                mime_type=stored.get('mime_type') or '',
                size_bytes=stored.get('size_bytes') or 0,
                duration_seconds=Decimal(str(stored['duration_seconds'])) if stored.get('duration_seconds') is not None else None,
                width=stored.get('width'),
                height=stored.get('height'),
                trim_start_seconds=Decimal(str(stored.get('trim_start_seconds') or 0)),
                trim_end_seconds=Decimal(str(stored['trim_end_seconds'])) if stored.get('trim_end_seconds') is not None else None,
                position=position,
            ))
    return created
