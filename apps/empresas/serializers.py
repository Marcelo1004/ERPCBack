from rest_framework import serializers
from .models import Empresa
from apps.suscripciones.serializers import SuscripcionSerializer

class EmpresaSerializer(serializers.ModelSerializer):
    suscripcion_detail = SuscripcionSerializer(source='suscripcion', read_only=True)
    # CAMBIO CRUCIAL: Usamos SerializerMethodField para evitar la importación circular
    admin_empresa_detail = serializers.SerializerMethodField() 

    class Meta:
        model = Empresa
        fields = [
            'id', 'nombre', 'nit', 'direccion', 'telefono', 'email_contacto',
            'logo', 'fecha_registro', 'suscripcion', 'suscripcion_detail',
            'admin_empresa', 'admin_empresa_detail', 'is_active'
        ]
        read_only_fields = ['fecha_registro']

    # Método para obtener los detalles del admin_empresa
    def get_admin_empresa_detail(self, obj):
        # Importamos UserProfileSerializer LOCALMENTE para evitar la importación circular global
        from apps.usuarios.serializers import UserProfileSerializer
        if obj.admin_empresa:
            # Puedes usar un serializer más ligero si no necesitas todos los detalles del perfil aquí
            # O usar UserProfileSerializer si es lo que necesitas.
            return UserProfileSerializer(obj.admin_empresa, context=self.context).data
        return None

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class EmpresaMarketplaceSerializer(serializers.ModelSerializer):
    """
    Serializer más ligero para mostrar empresas en el marketplace público.
    No expone detalles sensibles ni relaciones complejas.
    """
    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'descripcion_corta', 'direccion', 'is_active']