from django.contrib import admin
from .models import UserAccount, Subscription

admin.site.register(UserAccount)
admin.site.register(Subscription)