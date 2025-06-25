# apps/logs/serializers.py

from rest_framework import serializers
from .models import ActividadLog

class ActividadLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = ActividadLog
        fields = ['id', 'user', 'user_username', 'empresa', 'empresa_nombre', 'timestamp', 'activity_type', 'description', 'entity_id', 'entity_name']
        read_only_fields = ['user', 'empresa', 'timestamp'] # Estos campos se asignan en la lógica de la vista o signals