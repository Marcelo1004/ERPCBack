from rest_framework import serializers
from .models import Sucursal
from apps.empresas.serializers import EmpresaSerializer # Importa el serializador de Empresa

class SucursalSerializer(serializers.ModelSerializer):
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    class Meta:
        model = Sucursal
        fields = ['id', 'nombre', 'direccion', 'telefono', 'empresa', 'empresa_detail']
        extra_kwargs = {
            'empresa': {'write_only': True, 'required': False}
        }

