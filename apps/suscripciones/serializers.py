from rest_framework import serializers
from .models import Suscripcion

class SuscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suscripcion
        fields = ['id', 'nombre', 'descripcion', 'cantidad_usuarios_permitidos']

