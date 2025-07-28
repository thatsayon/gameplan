from django.urls import path
from .views import (
    ChatbotView,
    ChatbotHistoryView,
    ChatclassListView,
    CreateChatClassView,
)

urlpatterns = [
    path("chatbot/<uuid:session_id>/", ChatbotView.as_view()),
    path("chatclass/", ChatclassListView.as_view()),
    path("create-chat-class/", CreateChatClassView.as_view()),
    path("chat-history/<uuid:pk>/", ChatbotHistoryView.as_view()),
]