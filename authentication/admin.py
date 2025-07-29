from django.contrib import admin
from .models import UserAccount, Subscription, OTP

admin.site.register(UserAccount)
admin.site.register(Subscription)
admin.site.register(OTP)