from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('c/', include('chatbot.urls')),
    path('payments/', include('payments.urls')),
    path('o/', include('others.urls')),
]
