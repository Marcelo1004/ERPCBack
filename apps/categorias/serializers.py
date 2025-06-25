from rest_framework import serializers
from .models import Categoria
from apps.empresas.serializers import EmpresaSerializer # Importa el Serializer de Empresa

class CategoriaSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Categoria, adaptado para SaaS multi-empresa.
    Muestra los detalles de la empresa asociada de forma anidada para lectura.
    """
    # Campo de solo lectura para mostrar los detalles completos de la empresa
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    class Meta:
        model = Categoria
        # Incluye 'empresa' para escribir (enviar el ID) y 'empresa_detail' para leer
        fields = ['id', 'nombre', 'descripcion', 'empresa', 'empresa_detail']
        extra_kwargs = {
            # 'empresa' es para recibir el ID de la FK; no debe ser visible directamente en la respuesta para lectura.
            'empresa': {'write_only': True, 'required': False} # La empresa será asignada por el backend en la mayoría de los casos
        }

