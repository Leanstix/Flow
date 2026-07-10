from django.db import transaction
from django.db.models import Count, Prefetch, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import Notification
from notifications.services import create_notification

from .models import Community, CommunityMembership, CommunityPost, CommunityResource
from .permissions import IsCommunityContentAuthorOrModerator, IsCommunityOwnerOrReadOnly, active_membership, can_moderate
from .serializers import (
    CommunityMembershipSerializer,
    CommunityPostSerializer,
    CommunityResourceSerializer,
    CommunitySerializer,
)


class CommunityViewSet(viewsets.ModelViewSet):
    serializer_class = CommunitySerializer
    permission_classes = [IsAuthenticated, IsCommunityOwnerOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        current_memberships = CommunityMembership.objects.filter(user=user)
        queryset = Community.objects.filter(is_active=True).select_related('owner').prefetch_related(
            Prefetch('memberships', queryset=current_memberships, to_attr='current_memberships')
        ).annotate(
            active_members_count=Count('memberships', filter=Q(memberships__status=CommunityMembership.Status.ACTIVE), distinct=True),
            posts_count=Count('posts', distinct=True),
            resources_count=Count('resources', distinct=True),
        )

        query = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category', '').strip()
        course_code = self.request.query_params.get('course_code', '').strip()
        mine = self.request.query_params.get('mine') == 'true'

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(course_code__icontains=query)
            )
        if category:
            queryset = queryset.filter(category=category)
        if course_code:
            queryset = queryset.filter(course_code__iexact=course_code)
        if mine:
            queryset = queryset.filter(
                memberships__user=user,
                memberships__status=CommunityMembership.Status.ACTIVE,
            )
        return queryset.distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        community = serializer.save(owner=self.request.user)
        CommunityMembership.objects.create(
            community=community,
            user=self.request.user,
            role=CommunityMembership.Role.OWNER,
            status=CommunityMembership.Status.ACTIVE,
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])

    @action(detail=True, methods=['post'])
    def join(self, request, slug=None):
        community = self.get_object()
        membership, created = CommunityMembership.objects.get_or_create(
            community=community,
            user=request.user,
            defaults={
                'status': CommunityMembership.Status.ACTIVE
                if community.visibility == Community.Visibility.PUBLIC
                else CommunityMembership.Status.PENDING,
            },
        )

        if not created and membership.status == CommunityMembership.Status.ACTIVE:
            return Response({'detail': 'You are already a member.'}, status=status.HTTP_200_OK)

        if not created and membership.status == CommunityMembership.Status.PENDING:
            return Response({'detail': 'Your join request is pending.', 'status': membership.status}, status=status.HTTP_200_OK)

        if membership.status == CommunityMembership.Status.PENDING:
            create_notification(
                recipient=community.owner,
                actor=request.user,
                verb=Notification.Verb.SYSTEM,
                message=f'{request.user.user_name or request.user.email} requested to join {community.name}.',
            )

        return Response(
            {'detail': 'Joined successfully.' if membership.status == CommunityMembership.Status.ACTIVE else 'Join request submitted.', 'status': membership.status},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, slug=None):
        community = self.get_object()
        membership = CommunityMembership.objects.filter(community=community, user=request.user).first()
        if not membership:
            return Response({'detail': 'You are not a member.'}, status=status.HTTP_400_BAD_REQUEST)
        if membership.role == CommunityMembership.Role.OWNER:
            return Response({'detail': 'The owner cannot leave without transferring ownership.'}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def members(self, request, slug=None):
        community = self.get_object()
        membership = active_membership(request.user, community)
        if community.visibility == Community.Visibility.PRIVATE and not membership and not request.user.is_staff:
            raise PermissionDenied('Only members can view this private community roster.')

        queryset = community.memberships.select_related('user')
        if not can_moderate(request.user, community):
            queryset = queryset.filter(status=CommunityMembership.Status.ACTIVE)
        return Response(CommunityMembershipSerializer(queryset, many=True).data)

    @action(detail=True, methods=['post'], url_path='members/(?P<membership_id>[^/.]+)/approve')
    def approve_member(self, request, slug=None, membership_id=None):
        community = self.get_object()
        if not can_moderate(request.user, community):
            raise PermissionDenied('Only owners and moderators can approve members.')

        membership = community.memberships.filter(pk=membership_id, status=CommunityMembership.Status.PENDING).select_related('user').first()
        if not membership:
            raise ValidationError({'membership_id': 'Pending membership not found.'})
        membership.status = CommunityMembership.Status.ACTIVE
        membership.save(update_fields=['status'])
        create_notification(
            recipient=membership.user,
            actor=request.user,
            verb=Notification.Verb.SYSTEM,
            message=f'Your request to join {community.name} was approved.',
        )
        return Response(CommunityMembershipSerializer(membership).data)

    @action(detail=True, methods=['patch'], url_path='members/(?P<membership_id>[^/.]+)/role')
    def update_member_role(self, request, slug=None, membership_id=None):
        community = self.get_object()
        if community.owner_id != request.user.id and not request.user.is_staff:
            raise PermissionDenied('Only the owner can change member roles.')

        membership = community.memberships.filter(pk=membership_id, status=CommunityMembership.Status.ACTIVE).first()
        if not membership:
            raise ValidationError({'membership_id': 'Active membership not found.'})
        if membership.role == CommunityMembership.Role.OWNER:
            raise ValidationError({'role': 'Use ownership transfer to change the owner.'})

        role = request.data.get('role')
        if role not in {CommunityMembership.Role.MEMBER, CommunityMembership.Role.MODERATOR}:
            raise ValidationError({'role': 'Role must be member or moderator.'})
        membership.role = role
        membership.save(update_fields=['role'])
        return Response(CommunityMembershipSerializer(membership).data)


class CommunityPostViewSet(viewsets.ModelViewSet):
    serializer_class = CommunityPostSerializer
    permission_classes = [IsAuthenticated, IsCommunityContentAuthorOrModerator]

    def get_queryset(self):
        queryset = CommunityPost.objects.select_related('community', 'author').filter(community__is_active=True)
        community_slug = self.request.query_params.get('community')
        if community_slug:
            queryset = queryset.filter(community__slug=community_slug)
        if self.action in {'list', 'retrieve'}:
            private_ids = CommunityMembership.objects.filter(
                user=self.request.user,
                status=CommunityMembership.Status.ACTIVE,
            ).values_list('community_id', flat=True)
            queryset = queryset.filter(Q(community__visibility=Community.Visibility.PUBLIC) | Q(community_id__in=private_ids))
        return queryset

    def perform_create(self, serializer):
        community = serializer.validated_data['community']
        if not active_membership(self.request.user, community):
            raise PermissionDenied('Join this community before posting.')
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_pin(self, request, pk=None):
        post = self.get_object()
        if not can_moderate(request.user, post.community):
            raise PermissionDenied('Only owners and moderators can pin posts.')
        post.is_pinned = not post.is_pinned
        post.save(update_fields=['is_pinned', 'updated_at'])
        return Response(self.get_serializer(post).data)


class CommunityResourceViewSet(viewsets.ModelViewSet):
    serializer_class = CommunityResourceSerializer
    permission_classes = [IsAuthenticated, IsCommunityContentAuthorOrModerator]

    def get_queryset(self):
        queryset = CommunityResource.objects.select_related('community', 'uploaded_by').filter(community__is_active=True)
        community_slug = self.request.query_params.get('community')
        if community_slug:
            queryset = queryset.filter(community__slug=community_slug)
        member_ids = CommunityMembership.objects.filter(
            user=self.request.user,
            status=CommunityMembership.Status.ACTIVE,
        ).values_list('community_id', flat=True)
        return queryset.filter(community_id__in=member_ids)

    def perform_create(self, serializer):
        community = serializer.validated_data['community']
        if not active_membership(self.request.user, community):
            raise PermissionDenied('Join this community before adding resources.')
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_pin(self, request, pk=None):
        resource = self.get_object()
        if not can_moderate(request.user, resource.community):
            raise PermissionDenied('Only owners and moderators can pin resources.')
        resource.is_pinned = not resource.is_pinned
        resource.save(update_fields=['is_pinned'])
        return Response(self.get_serializer(resource).data)
