from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model
from .models import ChatHistory
from .serializers import (
    ChatbotSerializer
)
import requests

User = get_user_model()

class ChatbotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = ChatbotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fastapi_url = "http://127.0.0.1:8080/chat"

        # Get user's chat history (ordered)
        chat_history_qs = ChatHistory.objects.filter(user=user).order_by("created_at")
        chat_history = [
            {
                "user_message": entry.user_message,
                "bot_message": entry.bot_message
            }
            for entry in chat_history_qs
        ]

        payload = {
            "user_id": str(user.id),
            "message": serializer.validated_data['message'],
            "chat_history": chat_history
        }

        headers = {"Content-Type": "application/json"}

        # Send POST request to FastAPI
        response = requests.post(fastapi_url, json=payload, headers=headers)

        if response.status_code == 200:
            bot_response = response.json().get("response", "")

            ChatHistory.objects.create(
                user=user,
                user_message=serializer.validated_data['message'],
                bot_message=bot_response
            )
            return Response({"response": bot_response}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Error with FastAPI request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)