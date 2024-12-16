from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Advertisement, Message
from .serializers import AdvertisementSerializer, AdvertisementCreateSerializer, MessageSerializer, MessageCreateSerializer
from django.shortcuts import get_object_or_404

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
        advertisement_id = request.data.get("advertisement_id")
        content = request.data.get("content")
        try:
            advertisement = Advertisement.objects.get(id=advertisement_id)
            Message.objects.create(
                sender=request.user,
                receiver=advertisement.user,
                advertisement=advertisement,
                content=content,
            )
            return Response({"message": "Message sent successfully!"}, status=status.HTTP_201_CREATED)
        except Advertisement.DoesNotExist:
            return Response({"error": "Advertisement not found."}, status=status.HTTP_404_NOT_FOUND)
        
class SellerMessagesView(APIView):
    """
    Retrieve all messages sent to the seller for their advertisements.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        messages = Message.objects.filter(receiver=request.user).order_by("-sent_at")
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ReplyToMessageView(APIView):
    """
    Reply to a customer who messaged the seller.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MessageCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(sender=request.user)
            return Response({"message": "Reply sent successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CustomerMessagesView(APIView):
    """
    Retrieve all messages (including replies) sent to the customer by sellers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        messages = Message.objects.filter(receiver=request.user).order_by("-sent_at")
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    