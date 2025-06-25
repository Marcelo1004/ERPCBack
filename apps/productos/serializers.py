from rest_framework import serializers
from .models import Producto
from apps.categorias.serializers import CategoriaSerializer # Importa el Serializer de Categoria
from apps.almacenes.serializers import AlmacenSerializer   # Importa el Serializer de Almacen
from apps.empresas.serializers import EmpresaSerializer   # Importa el Serializer de Empresa

class ProductoSerializer(serializers.ModelSerializer):
    categoria_detail = CategoriaSerializer(source='categoria', read_only=True)
    almacen_detail = AlmacenSerializer(source='almacen', read_only=True)
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True) # Nuevo campo


    imagen = serializers.ImageField(required=False, allow_null=True)


    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'stock', 'imagen',
            'categoria', 'categoria_detail',
            'almacen', 'almacen_detail',
            'empresa', 'empresa_detail'
        ]
        extra_kwargs = {
            'categoria': {'write_only': True, 'required': False},
            'almacen': {'write_only': True, 'required': False},
            'empresa': {'write_only': True, 'required': False}
        }

