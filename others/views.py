from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.contrib.auth import get_user_model
from .models import HelpandSupport
from .serializers import (
    HelpandSupportSerializer
)

User = get_user_model()


class HelpandSupportView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = HelpandSupportSerializer
    queryset = HelpandSupport.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            {"detail": "Help and Support request created successfully"},
            status=status.HTTP_201_CREATED
        )