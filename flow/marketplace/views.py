from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Advertisement, Message
from .serializers import AdvertisementSerializer, AdvertisementCreateSerializer, MessageSerializer, MessageCreateSerializer
from django.shortcuts import get_object_or_404

def get_filtered_messages(user, sent=False):
    """
    Retrieve messages filtered by user role.
    """
    if sent:
        return Message.objects.filter(sender=user).order_by("-sent_at")
    return Message.objects.filter(receiver=user).order_by("-sent_at")

class AdvertisementListView(APIView):
    def get(self, request):
        advertisements = Advertisement.objects.all().order_by("-created_at")
        serializer = AdvertisementSerializer(advertisements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdvertisementCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AdvertisementCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdvertisementDetailView(APIView):
    def get(self, request, pk):
        advertisement = get_object_or_404(Advertisement, pk=pk)
        serializer = AdvertisementSerializer(advertisement)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        advertisement = get_object_or_404(Advertisement, id=request.data.get("advertisement_id"))
        content = request.data.get("content")
        Message.objects.create(
            sender=request.user,
            receiver=advertisement.user,
            advertisement=advertisement,
            content=content,
        )
        return Response({"message": "Message sent successfully!"}, status=status.HTTP_201_CREATED)

class SellerMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        messages = get_filtered_messages(user=request.user)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ReplyToMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        original_message_id = request.data.get("original_message_id")
        content = request.data.get("content")

        # Validate reply
        original_message = get_object_or_404(Message, id=original_message_id, receiver=request.user)
        reply_message = Message.objects.create(
            sender=request.user,
            receiver=original_message.sender,
            advertisement=original_message.advertisement,
            content=content,
        )
        return Response(
            {"message": "Reply sent successfully!", "reply_id": reply_message.id},
            status=status.HTTP_201_CREATED
        )

class CustomerMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        messages = get_filtered_messages(user=request.user, sent=False)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)