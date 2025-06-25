from rest_framework import serializers
from .models import Almacen
from apps.sucursales.serializers import SucursalSerializer # Importa el Serializer de Sucursal
from apps.empresas.serializers import EmpresaSerializer   # Importa el Serializer de Empresa

class AlmacenSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Almacen, adaptado para SaaS multi-empresa.
    Muestra los detalles de la sucursal y la empresa asociadas de forma anidada para lectura.
    """
    # Campos de solo lectura para mostrar los detalles completos de las FKs
    sucursal_detail = SucursalSerializer(source='sucursal', read_only=True)
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    class Meta:
        model = Almacen
        # Incluye las FKs para escribir (enviar el ID) y los *_detail para leer
        fields = ['id', 'nombre', 'ubicacion', 'capacidad', 'sucursal', 'sucursal_detail', 'empresa', 'empresa_detail']
        extra_kwargs = {
            # 'sucursal' y 'empresa' son para recibir los IDs de la FKs
            'sucursal': {'write_only': True, 'required': False},
            'empresa': {'write_only': True, 'required': False} # La empresa será asignada por el backend en la mayoría de los casos
        }

