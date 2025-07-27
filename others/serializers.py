from rest_framework import serializers
from .models import HelpandSupport

class HelpandSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpandSupport
        fields = ['email', 'description']