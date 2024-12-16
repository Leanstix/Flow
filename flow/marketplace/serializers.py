from rest_framework import serializers
from .models import Advertisement, AdvertisementImage, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class AdvertisementImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvertisementImage
        fields = ["id", "image"]

class AdvertisementSerializer(serializers.ModelSerializer):
    images = AdvertisementImageSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField()

    class Meta:
        model = Advertisement
        fields = ["id", "user", "title", "description", "images", "created_at"]

class AdvertisementCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = Advertisement
        fields = ["id", "title", "description", "images"]

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        advertisement = Advertisement.objects.create(**validated_data)
        for image in images:
            AdvertisementImage.objects.create(advertisement=advertisement, image=image)
        return advertisement

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField()
    receiver = serializers.StringRelatedField()

    class Meta:
        model = Message
        fields = ["id", "sender", "receiver", "advertisement", "content", "sent_at"]

class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["receiver", "advertisement", "content"]

    def validate(self, data):
        if data["receiver"] == self.context["request"].user:
            raise serializers.ValidationError("You cannot send a message to yourself.")
        return data
    