from django.db import transaction
from rest_framework import serializers

from .models import Advertisement, AdvertisementImage, Report


class MarketplaceUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    user_name = serializers.CharField(allow_blank=True, allow_null=True)
    first_name = serializers.CharField(allow_blank=True, allow_null=True)
    last_name = serializers.CharField(allow_blank=True, allow_null=True)
    profile_picture = serializers.URLField(allow_blank=True, allow_null=True)
    department = serializers.CharField(allow_blank=True, allow_null=True)


class AdvertisementImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvertisementImage
        fields = ['id', 'image', 'position']
        read_only_fields = fields


class AdvertisementSerializer(serializers.ModelSerializer):
    seller = MarketplaceUserSerializer(source='user', read_only=True)
    images = AdvertisementImageSerializer(many=True, read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    saved_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Advertisement
        fields = [
            'id', 'seller', 'title', 'description', 'price', 'currency',
            'category', 'condition', 'status', 'location', 'image', 'images',
            'views_count', 'saved_count', 'is_saved', 'is_owner', 'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_is_saved(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.saved_by.filter(user=request.user).exists())

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


class AdvertisementWriteSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=6,
    )

    class Meta:
        model = Advertisement
        fields = [
            'title', 'description', 'price', 'currency', 'category',
            'condition', 'status', 'location', 'image', 'images',
        ]
        extra_kwargs = {
            'status': {'required': False},
            'currency': {'required': False},
            'image': {'required': False},
        }

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError('Title must contain at least 3 characters.')
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Description must contain at least 10 characters.')
        return value

    def validate_currency(self, value):
        value = value.upper().strip()
        if value != 'NGN':
            raise serializers.ValidationError('Only NGN listings are supported currently.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        uploads = list(request.FILES.getlist('images')) if request else []
        primary = attrs.get('image')
        all_uploads = uploads + ([primary] if primary and primary not in uploads else [])
        if len(all_uploads) > 6:
            raise serializers.ValidationError({'images': 'A listing can contain at most 6 images.'})
        for upload in all_uploads:
            if upload.size > 8 * 1024 * 1024:
                raise serializers.ValidationError({'images': 'Each image must be 8 MB or smaller.'})
            content_type = getattr(upload, 'content_type', '')
            if content_type and content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise serializers.ValidationError({'images': 'Images must be JPEG, PNG, or WebP.'})
        return attrs

    def _images(self):
        request = self.context.get('request')
        return list(request.FILES.getlist('images')) if request else []

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('images', None)
        uploads = self._images()
        advertisement = Advertisement.objects.create(**validated_data)
        for position, image in enumerate(uploads):
            AdvertisementImage.objects.create(advertisement=advertisement, image=image, position=position)
        return advertisement

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop('images', None)
        uploads = self._images()
        instance = super().update(instance, validated_data)
        if uploads:
            instance.images.all().delete()
            for position, image in enumerate(uploads):
                AdvertisementImage.objects.create(advertisement=instance, image=image, position=position)
        return instance


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'advertisement', 'reason', 'reported_at']
        read_only_fields = ['id', 'reported_at']

    def validate_reason(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Provide at least 10 characters explaining the report.')
        return value
