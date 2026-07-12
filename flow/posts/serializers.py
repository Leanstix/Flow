from rest_framework import serializers

from .models import Comment, Hashtag, Like, Post, PostMedia, Report
from .services import create_post_media, parse_media_metadata, sync_post_entities


def user_payload(user):
    return {
        'id': user.id,
        'username': user.user_name,
        'user_name': user.user_name,
        'email': user.email,
        'profile_picture': user.profile_picture,
    }


def absolute_media_url(request, value):
    if not value:
        return ''
    if value.startswith(('http://', 'https://')) or not request:
        return value
    return request.build_absolute_uri(value)


class PostMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PostMedia
        fields = [
            'id', 'media_type', 'url', 'thumbnail_url', 'file_name', 'mime_type',
            'size_bytes', 'duration_seconds', 'width', 'height',
            'trim_start_seconds', 'trim_end_seconds', 'position',
        ]
        read_only_fields = fields

    def get_url(self, obj):
        return absolute_media_url(self.context.get('request'), obj.url)

    def get_thumbnail_url(self, obj):
        return absolute_media_url(self.context.get('request'), obj.thumbnail_url)


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    post = serializers.IntegerField(source='post_id', read_only=True)
    parent = serializers.IntegerField(source='parent_id', read_only=True)
    root = serializers.IntegerField(source='root_id', read_only=True)
    parent_preview = serializers.SerializerMethodField()
    replies_count = serializers.ReadOnlyField()
    mentions = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'parent', 'root', 'depth', 'parent_preview', 'user',
            'content', 'created_at', 'replies_count', 'mentions',
        ]
        read_only_fields = [
            'id', 'post', 'parent', 'root', 'depth', 'parent_preview', 'user',
            'created_at', 'replies_count', 'mentions',
        ]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Comment content cannot be empty.')
        value = value.strip()
        if len(value) > 5000:
            raise serializers.ValidationError('Comment content cannot exceed 5000 characters.')
        return value

    def get_user(self, obj):
        return user_payload(obj.user)

    def get_parent_preview(self, obj):
        if not obj.parent_id:
            return None
        return {
            'id': obj.parent_id,
            'user': user_payload(obj.parent.user),
            'content': obj.parent.content,
        }

    def get_mentions(self, obj):
        return [user_payload(user) for user in obj.mentioned_users.all()]


class PostSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    likes_count = serializers.ReadOnlyField()
    comments_count = serializers.ReadOnlyField()
    reposts_count = serializers.ReadOnlyField()
    has_liked = serializers.SerializerMethodField()
    reposted_from = serializers.SerializerMethodField()
    media = PostMediaSerializer(many=True, read_only=True)
    hashtags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    mentions = serializers.SerializerMethodField()
    media_metadata = serializers.CharField(write_only=True, required=False, allow_blank=True)
    platform = serializers.ChoiceField(choices=['web', 'mobile'], write_only=True, required=False)

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'created_at', 'reposted_from', 'media',
            'hashtags', 'mentions', 'likes_count', 'comments_count',
            'reposts_count', 'has_liked', 'media_metadata', 'platform',
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'likes_count', 'comments_count',
            'reposts_count', 'has_liked', 'reposted_from', 'media', 'hashtags',
            'mentions',
        ]
        extra_kwargs = {
            'content': {'required': False, 'allow_blank': True},
        }

    def validate_content(self, value):
        value = (value or '').strip()
        if len(value) > 10000:
            raise serializers.ValidationError('Post content cannot exceed 10000 characters.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        uploads = list(request.FILES.getlist('media')) if request else []
        content = attrs.get('content', '')
        if not content and not uploads:
            raise serializers.ValidationError({'content': 'Write something or attach media.'})

        platform = attrs.get('platform')
        metadata = parse_media_metadata(attrs.get('media_metadata'))
        if uploads and metadata and len(metadata) != len(uploads):
            raise serializers.ValidationError({'media_metadata': 'Provide one metadata object for every media file.'})
        if platform == 'web':
            for item in metadata:
                if not isinstance(item, dict):
                    continue
                duration = item.get('trim_end_seconds')
                if duration not in (None, ''):
                    duration = float(duration) - float(item.get('trim_start_seconds') or 0)
                else:
                    duration = float(item.get('duration_seconds') or 0)
                if duration > 90:
                    raise serializers.ValidationError({'media': 'Web videos must be 90 seconds or shorter.'})
        attrs['_parsed_media_metadata'] = metadata
        return attrs

    def create(self, validated_data):
        metadata = validated_data.pop('_parsed_media_metadata', [])
        validated_data.pop('media_metadata', None)
        platform = validated_data.pop('platform', None)
        request = self.context.get('request')
        post = Post.objects.create(**validated_data)
        try:
            create_post_media(
                post,
                request,
                metadata,
                max_video_seconds=90 if platform == 'web' else 180,
            )
            sync_post_entities(post, post.user)
        except Exception:
            post.delete()
            raise
        return post

    def get_user(self, obj):
        return user_payload(obj.user)

    def get_has_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_mentions(self, obj):
        return [user_payload(user) for user in obj.mentioned_users.all()]

    def get_reposted_from(self, obj):
        if not obj.reposted_from:
            return None
        original = obj.reposted_from
        return {
            'id': original.id,
            'user': user_payload(original.user),
            'content': original.content,
            'created_at': original.created_at,
            'media': PostMediaSerializer(original.media.all(), many=True, context=self.context).data,
            'hashtags': [item.name for item in original.hashtags.all()],
        }


class HashtagSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Hashtag
        fields = ['name', 'posts_count']
        read_only_fields = fields


class LikeSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def get_user(self, obj):
        return user_payload(obj.user)


class ReportSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'user', 'post', 'reason', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def get_user(self, obj):
        return user_payload(obj.user)
