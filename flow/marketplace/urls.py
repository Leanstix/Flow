from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from .views import SendMessageView, ReportAdvertisementView, ConversationMessagesView, CustomerMessagesView, AdvertisementListView, AdvertisementCreateView, AdvertisementDetailView, SellerMessagesView, ReplyToMessageView

urlpatterns = [
    path("messages/send/", SendMessageView.as_view(), name="send_message"),
    path("", AdvertisementListView.as_view(), name="advertisement_list"),
    path("create/", AdvertisementCreateView.as_view(), name="advertisement_create"),
    path("<int:pk>/", AdvertisementDetailView.as_view(), name="advertisement_detail"),
    path("messages/seller/", SellerMessagesView.as_view(), name="seller_messages"),
    path("messages/reply/", ReplyToMessageView.as_view(), name="reply_to_message"),
    path("messages/customer/", CustomerMessagesView.as_view(), name="customer_messages"),
    path("advertisements/report/", ReportAdvertisementView.as_view(), name="report_advertisement"),
    path("messages/conversations/<uuid:conversation_id>/", ConversationMessagesView.as_view(), name="conversation_messages"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
