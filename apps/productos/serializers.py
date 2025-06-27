from rest_framework import serializers
from .models import Producto
from apps.categorias.serializers import CategoriaSerializer
from apps.almacenes.serializers import AlmacenSerializer
from apps.empresas.serializers import EmpresaSerializer
from decimal import Decimal  # <--- IMPORTANT: Add this import!


class ProductoSerializer(serializers.ModelSerializer):
    categoria_detail = CategoriaSerializer(source='categoria', read_only=True)
    almacen_detail = AlmacenSerializer(source='almacen', read_only=True)
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    imagen = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'stock', 'imagen',
            'categoria', 'categoria_detail',
            'almacen', 'almacen_detail',
            'empresa', 'empresa_detail',
            'descuento','is_active'  # Ensure 'descuento' is in fields
        ]
        extra_kwargs = {
            'categoria': {'write_only': True, 'required': False},
            'almacen': {'write_only': True, 'required': False},
            'empresa': {'write_only': True, 'required': False},
            # If descuento is not always required, you might want this:
            # 'descuento': {'required': False, 'allow_null': True}
        }

    # --- Add this custom validation for the 'descuento' field ---
    def validate_descuento(self, value):
        if value is None:
            # If the value is None, return a default Decimal with correct precision
            return Decimal('0.0000')

        try:
            # Convert the value to a Decimal and quantize it to 4 decimal places.
            # This assumes your Producto model's 'descuento' field has decimal_places=4.
            decimal_value = Decimal(str(value)).quantize(Decimal('0.0000'))
        except Exception:
            raise serializers.ValidationError("El descuento debe ser un número válido.")

        # Validate that the discount is within an acceptable range (e.g., 0 to 1 for percentage)
        if not (Decimal('0.0000') <= decimal_value <= Decimal('1.0000')):
            raise serializers.ValidationError("El descuento debe ser un valor entre 0.00 y 1.00.")

        return decimal_value
class ProductoListSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'precio', 'stock', 'imagen',
            'categoria_nombre', 'empresa_nombre',
            'descuento', 'is_active' # Include is_active if it's relevant for public listing
        ]