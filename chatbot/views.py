from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.db.models import F
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from authentication.models import Subscription
from .models import ChatHistory, ChatClass, SavedChat, FreeLimit
from .serializers import (
    ChatbotSerializer,
    ChatHistorySerializer,
    ChatClassSerializer,
    ChatClassCreateSerializer,
    ChatbotSaveSerializer,
    ChatbotListSerializer
)
import requests

User = get_user_model()

class ChatbotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id=None):
        user = request.user
        active_sub = Subscription.objects.filter(user=user).order_by('-start_date').first()

        # Check if user has reached their free limit
        if FreeLimit.objects.filter(user=user).first().limit > 5 and active_sub.subscription_type == 'free':
            return Response({"detail": "You have reached your free limit."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ChatbotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 👇 Extract the JWT token from the request headers
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response({"detail": "Invalid token header."}, status=400)

        jwt_token = auth_header.split(" ")[1]

        fastapi_url = "http://127.0.0.1:8011/chat"

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


            # Increment the free limit
            FreeLimit.objects.filter(user=user).update(limit=F('limit') + 1)

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

class ChatbotSavedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        serializer = ChatbotSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pin_date = request.data.get('pin_date')
        if not pin_date:
            return Response({"message": "Please provide a pin date."}, status=status.HTTP_400_BAD_REQUEST)
        chat_class = get_object_or_404(ChatClass, id=session_id)

        SavedChat.objects.create(
            user=user,
            chat_class=chat_class,
            pin_date=pin_date
        )

        return Response({"message": "chat saved successfully"}, status=status.HTTP_501_NOT_IMPLEMENTED)

class ChatbotListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatbotListSerializer
    
    def get_queryset(self):
        user = self.request.user
        return SavedChat.objects.filter(user=user).distinct()

class EexportChatHistory(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, class_id):
        chat_class = get_object_or_404(ChatClass, id=class_id)
        histories = chat_class.chathistory_set.all()

        if not histories.exists():
            return Response({"message": "No chat history found."}, status=status.HTTP_404_NOT_FOUND)

        # Create PDF in memory
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50

        for history in histories:
            user_msg = f"User: {history.user_message}"
            bot_msg = f"Bot: {history.bot_message}"

            for line in [user_msg, bot_msg]:
                if len(line) > 100:
                    parts = [line[i:i+100] for i in range(0, len(line), 100)]
                    for part in parts:
                        pdf.drawString(50, y, part)
                        y -= 20
                else:
                    pdf.drawString(50, y, line)
                    y -= 20
            y -= 10  # Extra space between conversations

            if y < 60:
                pdf.showPage()
                y = height - 50

        pdf.save()
        buffer.seek(0)

        filename = f"chat_history_{chat_class.id}.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')