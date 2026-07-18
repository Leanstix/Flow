from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from flow.media import ensure_video_delivery_url, store_upload


@override_settings(CLOUDINARY_URL='cloudinary://key:secret@example')
class VideoDeliveryTests(SimpleTestCase):
    def test_existing_extensionless_cloudinary_urls_are_forced_to_video(self):
        old_url = 'https://res.cloudinary.com/demo/video/upload/c_limit,f_auto,q_auto/flow/posts/clip'

        self.assertEqual(
            ensure_video_delivery_url(old_url),
            'https://res.cloudinary.com/demo/video/upload/c_limit,f_auto:video,q_auto/flow/posts/clip',
        )

    def test_non_cloudinary_urls_are_not_rewritten(self):
        value = 'https://cdn.example/video.mp4'
        self.assertEqual(ensure_video_delivery_url(value), value)

    @patch('flow.media.cloudinary_url')
    @patch('flow.media.cloudinary.uploader.upload')
    def test_post_video_delivery_is_constrained_to_video_media(self, upload, build_url):
        upload.return_value = {'public_id': 'flow/posts/videos/clip', 'duration': 30}
        build_url.side_effect = [
            ('https://cdn.example/video.mp4', {}),
            ('https://cdn.example/poster.jpg', {}),
        ]
        video = SimpleUploadedFile('clip.mp4', b'video', content_type='video/mp4')

        store_upload(video, folder='flow/posts/videos', kind='video', declared_duration_seconds=30)

        video_transform = build_url.call_args_list[0].kwargs
        self.assertEqual(video_transform['resource_type'], 'video')
        self.assertEqual(video_transform['fetch_format'], 'auto:video')
