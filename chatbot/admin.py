from django.contrib import admin
from .models import (
    ChatClass,
    ChatHistory
)

admin.site.register(ChatClass)
admin.site.register(ChatHistory)