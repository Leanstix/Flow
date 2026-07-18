from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from flow.media import store_upload


@override_settings(CLOUDINARY_URL='cloudinary://key:secret@example')
class VideoDeliveryTests(SimpleTestCase):
    @patch('flow.media.cloudinary_url')
    @patch('flow.media.cloudinary.uploader.upload')
    def test_post_video_delivery_preserves_audio_as_aac(self, upload, build_url):
        upload.return_value = {'public_id': 'flow/posts/videos/clip', 'duration': 30}
        build_url.side_effect = [
            ('https://cdn.example/video.mp4', {}),
            ('https://cdn.example/poster.jpg', {}),
        ]
        video = SimpleUploadedFile('clip.mp4', b'video', content_type='video/mp4')

        store_upload(video, folder='flow/posts/videos', kind='video', declared_duration_seconds=30)

        video_transform = build_url.call_args_list[0].kwargs
        self.assertEqual(video_transform['resource_type'], 'video')
        self.assertEqual(video_transform['audio_codec'], 'aac')
