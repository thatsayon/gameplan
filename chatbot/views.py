from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import ChatHistory, ChatClass
from .serializers import (
    ChatbotSerializer,
    ChatHistorySerializer,
    ChatClassSerializer,
    ChatClassCreateSerializer,
)
import requests

User = get_user_model()

class ChatbotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id=None):
        user = request.user
        serializer = ChatbotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 👇 Extract the JWT token from the request headers
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response({"detail": "Invalid token header."}, status=400)

        jwt_token = auth_header.split(" ")[1]

        fastapi_url = "http://127.0.0.1:8001/chat"

        payload = {
            "message": serializer.validated_data['message'],
            "session_id": str(session_id),  # Convert UUID to string
            "user_id": 1,  # Convert UUID to string
            "access_token": jwt_token  # 👈 Pass JWT to FastAPI
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(fastapi_url, json=payload, headers=headers)
        except requests.RequestException:
            return Response({"detail": "Failed to connect to FastAPI."}, status=status.HTTP_502_BAD_GATEWAY)

        if response.status_code == 200:
            bot_response = response.json().get("response", "")

            # Assuming session_id corresponds to a ChatClass object
            chat_class = ChatClass.objects.get(id=session_id)

            # Now create the ChatHistory object
            ChatHistory.objects.create(
                parent=chat_class,  # Reference to ChatClass
                user=user,
                user_message=serializer.validated_data['message'],
                bot_message=bot_response
            )

            return Response({"response": bot_response}, status=status.HTTP_200_OK)

        return Response({"detail": "Error from FastAPI."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateChatClassView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatClassCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatclassListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatClassSerializer

    def get_queryset(self):
        user = self.request.user
        return ChatClass.objects.filter(user=user).distinct()

class ChatbotHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        chat_class = get_object_or_404(ChatClass, id=pk)
        histories = chat_class.chathistory_set.all()  # or use 'chat_class.histories.all()' if you set related_name
        serializer = ChatHistorySerializer(histories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)