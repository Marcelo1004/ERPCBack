# dashboard/serializers.py (o donde tengas tu serializador)

from rest_framework import serializers

# -----------------------------------------------------------
# Serializadores Anidados para las nuevas métricas
# -----------------------------------------------------------

class MonthlySalesSerializer(serializers.Serializer):
    """
    Serializador para las ventas mensuales.
    Corresponde a la interfaz { name: string; Ventas: number; }
    """
    name = serializers.CharField(max_length=50) # Nombre del mes (Ene, Feb, etc.)
    Ventas = serializers.DecimalField(max_digits=15, decimal_places=2) # El valor de ventas para el mes

class TopProductSerializer(serializers.Serializer):
    """
    Serializador para los productos más vendidos.
    Corresponde a la interfaz { name: string; sales: number; units: number; }
    """
    name = serializers.CharField(max_length=255) # Nombre del producto
    sales = serializers.DecimalField(max_digits=15, decimal_places=2) # Ventas totales en valor monetario
    units = serializers.IntegerField() # Cantidad de unidades vendidas

class CategoryDistributionSerializer(serializers.Serializer):
    """
    Serializador para la distribución de productos por categoría.
    Corresponde a la interfaz { name: string; products_count: number; }
    """
    name = serializers.CharField(max_length=255) # Nombre de la categoría
    products_count = serializers.IntegerField() # Cantidad de productos en esa categoría

class WarehouseInventorySerializer(serializers.Serializer):
    """
    Serializador para el detalle de inventario por almacén.
    Corresponde a la interfaz { name: string; total_value: number; product_count: number; }
    """
    name = serializers.CharField(max_length=255) # Nombre del almacén
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2) # Valor total del inventario en el almacén
    product_count = serializers.IntegerField() # Cantidad de productos únicos en el almacén


# -----------------------------------------------------------
# Serializador Principal del Dashboard
# -----------------------------------------------------------

class DashboardERPSerializer(serializers.Serializer):
    # Métricas existentes
    total_usuarios = serializers.IntegerField(default=0)
    total_sucursales = serializers.IntegerField(default=0)
    total_almacenes = serializers.IntegerField(default=0)
    total_categorias = serializers.IntegerField(default=0)
    total_productos = serializers.IntegerField(default=0)
    valor_total_inventario = serializers.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    productos_bajo_stock = serializers.ListField(child=serializers.CharField(), default=[])

    # Métricas de SuperUsuario (ya existentes)
    total_empresas = serializers.IntegerField(default=0, required=False)
    distribucion_suscripciones = serializers.ListField(
        child=serializers.DictField(), default=[], required=False
    )

    # NUEVAS MÉTRICAS AÑADIDAS
    monthly_sales = MonthlySalesSerializer(many=True, required=False) # Lista de ventas mensuales
    top_products = TopProductSerializer(many=True, required=False) # Lista de productos más vendidos
    category_distribution = CategoryDistributionSerializer(many=True, required=False) # Lista de distribución por categoría
    inventory_by_warehouse = WarehouseInventorySerializer(many=True, required=False) # Lista de inventario por almacén