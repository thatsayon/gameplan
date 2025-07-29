from rest_framework import serializers
from .models import (
    ChatHistory,
    ChatClass,
)

class ChatbotSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=100)

class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = "__all__"

class ChatClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatClass
        fields = "__all__"
    
class ChatbotSaveSerializer(serializers.Serializer):
    pin_date = serializers.DateTimeField(required=True)

class ChatClassCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatClass
        fields = ['id', 'chat_class']

        def create(self, validated_data):
            user = validated_data.pop('user')
            chat_class = ChatClass.objects.create(user=user, **validated_data)
            return chat_class