from django.contrib import admin
from .models import (
    ChatClass,
    ChatHistory,
    SavedChat,
    FreeLimit,
)

admin.site.register(ChatClass)
admin.site.register(ChatHistory)
admin.site.register(SavedChat)
admin.site.register(FreeLimit)