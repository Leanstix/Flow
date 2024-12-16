from django.contrib import admin
from .models import Advertisement, AdvertisementImage, Message

class AdvertisementImageInline(admin.TabularInline):
    model = AdvertisementImage
    extra = 1

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    inlines = [AdvertisementImageInline]

admin.site.register(Message)
