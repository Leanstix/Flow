from rest_framework import serializers

from .models import Community, CommunityMembership, CommunityPost, CommunityResource
from .permissions import can_moderate


def user_payload(user):
    return {
        'id': user.id,
        'email': user.email,
        'user_name': user.user_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_picture': user.profile_picture,
        'department': user.department,
    }


class CommunityMembershipSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = CommunityMembership
        fields = ['id', 'user', 'role', 'status', 'joined_at']
        read_only_fields = fields

    def get_user(self, obj):
        return user_payload(obj.user)


class CommunitySerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    active_members_count = serializers.IntegerField(read_only=True)
    posts_count = serializers.IntegerField(read_only=True)
    resources_count = serializers.IntegerField(read_only=True)
    membership_status = serializers.SerializerMethodField()
    membership_role = serializers.SerializerMethodField()
    can_moderate = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'visibility',
            'course_code', 'cover_image', 'owner', 'is_active', 'created_at',
            'updated_at', 'active_members_count', 'posts_count',
            'resources_count', 'membership_status', 'membership_role',
            'can_moderate',
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'created_at', 'updated_at',
            'active_members_count', 'posts_count', 'resources_count',
            'membership_status', 'membership_role', 'can_moderate',
        ]

    def validate(self, attrs):
        category = attrs.get('category', getattr(self.instance, 'category', None))
        course_code = attrs.get('course_code', getattr(self.instance, 'course_code', ''))
        if category == Community.Category.COURSE and not str(course_code or '').strip():
            raise serializers.ValidationError({'course_code': 'Course groups require a course code.'})
        return attrs

    def get_owner(self, obj):
        return user_payload(obj.owner)

    def _membership(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return None
        prefetched = getattr(obj, 'current_memberships', None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None
        return obj.memberships.filter(user=request.user).first()

    def get_membership_status(self, obj):
        membership = self._membership(obj)
        return membership.status if membership else None

    def get_membership_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    def get_can_moderate(self, obj):
        request = self.context.get('request')
        return bool(request and can_moderate(request.user, obj))


class CommunityPostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = ['id', 'community', 'author', 'content', 'attachment_url', 'is_pinned', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'is_pinned', 'created_at', 'updated_at']

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Post content cannot be empty.')
        return value

    def get_author(self, obj):
        return user_payload(obj.author)


class CommunityResourceSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()

    class Meta:
        model = CommunityResource
        fields = ['id', 'community', 'uploaded_by', 'title', 'description', 'url', 'is_pinned', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'is_pinned', 'created_at']

    def get_uploaded_by(self, obj):
        return user_payload(obj.uploaded_by)
