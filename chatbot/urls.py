from django.urls import path
from .views import (
    ChatbotView,
    ChatbotHistoryView,
    ChatclassListView,
    CreateChatClassView,
    ChatbotSavedView,
    EexportChatHistory,
)

urlpatterns = [
    path("chatbot/<uuid:session_id>/", ChatbotView.as_view()),
    path("chatclass/", ChatclassListView.as_view()),
    path("create-chat-class/", CreateChatClassView.as_view()),
    path("chat-history/<uuid:pk>/", ChatbotHistoryView.as_view()),
    path("chat-save/<uuid:session_id>/", ChatbotSavedView.as_view()),
    path("export-chat-history/<uuid:class_id>/", EexportChatHistory.as_view()),
]