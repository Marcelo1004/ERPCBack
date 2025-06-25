# apps/compras_proveedores/serializers.py

from rest_framework import serializers
from .models import Proveedor

class ProveedorSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Proveedor.
    """
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Proveedor
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
        extra_kwargs = {
            'nombre': {'error_messages': {'required': 'El nombre del proveedor es requerido.'}},
            'empresa': {'error_messages': {'required': 'La empresa es requerida.'}},
        }

# No añadimos los serializadores de Compra/DetalleCompra aún.