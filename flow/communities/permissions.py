from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import CommunityMembership


def active_membership(user, community):
    if not user or user.is_anonymous:
        return None
    return CommunityMembership.objects.filter(
        user=user,
        community=community,
        status=CommunityMembership.Status.ACTIVE,
    ).first()


def can_moderate(user, community):
    membership = active_membership(user, community)
    return bool(
        user
        and not user.is_anonymous
        and (
            user.is_staff
            or community.owner_id == user.id
            or membership
            and membership.role in {CommunityMembership.Role.OWNER, CommunityMembership.Role.MODERATOR}
        )
    )


class IsCommunityOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or obj.owner_id == request.user.id


class IsCommunityContentAuthorOrModerator(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        author_id = getattr(obj, 'author_id', None) or getattr(obj, 'uploaded_by_id', None)
        return author_id == request.user.id or can_moderate(request.user, obj.community)
