from decimal import Decimal, InvalidOperation

from django.db.models import Count, F, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Advertisement, Report, SavedAdvertisement
from .serializers import AdvertisementSerializer, AdvertisementWriteSerializer, ReportSerializer


class AdvertisementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Advertisement.objects.select_related('user').prefetch_related('images', 'saved_by').annotate(
            saved_count=Count('saved_by', distinct=True)
        )

        if self.action not in {'mine'}:
            queryset = queryset.exclude(status=Advertisement.Status.ARCHIVED)

        query = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category', '').strip()
        condition = self.request.query_params.get('condition', '').strip()
        listing_status = self.request.query_params.get('status', '').strip()
        seller = self.request.query_params.get('seller', '').strip()
        min_price = self.request.query_params.get('min_price', '').strip()
        max_price = self.request.query_params.get('max_price', '').strip()
        ordering = self.request.query_params.get('ordering', '-created_at')

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(location__icontains=query)
                | Q(user__user_name__icontains=query)
            )
        if category:
            queryset = queryset.filter(category=category)
        if condition:
            queryset = queryset.filter(condition=condition)
        if listing_status:
            queryset = queryset.filter(status=listing_status)
        elif self.action == 'list':
            queryset = queryset.filter(status__in=[Advertisement.Status.ACTIVE, Advertisement.Status.RESERVED])
        if seller:
            queryset = queryset.filter(user_id=seller)

        try:
            if min_price:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            if max_price:
                queryset = queryset.filter(price__lte=Decimal(max_price))
        except InvalidOperation as exc:
            raise ValidationError({'price': 'Price filters must be valid numbers.'}) from exc

        allowed_ordering = {
            'created_at', '-created_at', 'price', '-price',
            'views_count', '-views_count', 'saved_count', '-saved_count',
        }
        if ordering not in allowed_ordering:
            ordering = '-created_at'
        return queryset.order_by(ordering)

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return AdvertisementWriteSerializer
        return AdvertisementSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advertisement = serializer.save(user=request.user)
        return Response(
            AdvertisementSerializer(advertisement, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        advertisement = self.get_object()
        self._assert_owner(advertisement)
        serializer = self.get_serializer(advertisement, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        advertisement = serializer.save()
        return Response(AdvertisementSerializer(advertisement, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        advertisement = self.get_object()
        self._assert_owner(advertisement)
        advertisement.status = Advertisement.Status.ARCHIVED
        advertisement.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        advertisement = self.get_object()
        if advertisement.user_id != request.user.id:
            Advertisement.objects.filter(pk=advertisement.pk).update(views_count=F('views_count') + 1)
            advertisement.refresh_from_db(fields=['views_count'])
        return Response(AdvertisementSerializer(advertisement, context={'request': request}).data)

    def _assert_owner(self, advertisement):
        if advertisement.user_id != self.request.user.id and not self.request.user.is_staff:
            raise PermissionDenied('Only the seller can manage this listing.')

    @action(detail=False, methods=['get'])
    def mine(self, request):
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = AdvertisementSerializer(page if page is not None else queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=False, methods=['get'])
    def saved(self, request):
        queryset = self.get_queryset().filter(saved_by__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = AdvertisementSerializer(page if page is not None else queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=True, methods=['post'])
    def save_listing(self, request, pk=None):
        advertisement = self.get_object()
        if advertisement.user_id == request.user.id:
            raise ValidationError({'detail': 'You cannot save your own listing.'})
        _, created = SavedAdvertisement.objects.get_or_create(user=request.user, advertisement=advertisement)
        return Response({'saved': True}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def unsave(self, request, pk=None):
        advertisement = self.get_object()
        SavedAdvertisement.objects.filter(user=request.user, advertisement=advertisement).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        advertisement = self.get_object()
        if advertisement.user_id == request.user.id:
            raise ValidationError({'detail': 'You cannot report your own listing.'})
        serializer = ReportSerializer(data={'advertisement': advertisement.id, 'reason': request.data.get('reason', '')})
        serializer.is_valid(raise_exception=True)
        report, created = Report.objects.get_or_create(
            reporter=request.user,
            advertisement=advertisement,
            defaults={'reason': serializer.validated_data['reason']},
        )
        if not created:
            report.reason = serializer.validated_data['reason']
            report.save(update_fields=['reason'])
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        advertisement = self.get_object()
        self._assert_owner(advertisement)
        next_status = request.data.get('status')
        if next_status not in Advertisement.Status.values:
            raise ValidationError({'status': 'Invalid listing status.'})
        advertisement.status = next_status
        advertisement.save(update_fields=['status', 'updated_at'])
        return Response(AdvertisementSerializer(advertisement, context={'request': request}).data)
