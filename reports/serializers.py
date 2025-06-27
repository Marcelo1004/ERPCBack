# reports/serializers.py

from rest_framework import serializers
from decimal import Decimal # Necesario para los cálculos y tipos de datos

# --- Serializador para el Resumen de Ventas ---
class SalesSummaryReportSerializer(serializers.Serializer):
    total_ventas_cantidad = serializers.IntegerField(help_text="Número total de ventas.")
    monto_total_ventas = serializers.DecimalField(max_digits=15, decimal_places=2, help_text="Monto total de todas las ventas.")
    promedio_por_venta = serializers.DecimalField(max_digits=15, decimal_places=2, help_text="Monto promedio por venta.")

# --- Serializador para Productos Más Vendidos ---
class TopSellingProductReportSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID del Producto.")
    nombre = serializers.CharField(max_length=255, help_text="Nombre del Producto.")
    cantidad_vendida = serializers.IntegerField(help_text="Cantidad total vendida de este producto.")
    ingresos_generados = serializers.DecimalField(max_digits=15, decimal_places=2, help_text="Ingresos totales generados por este producto.")

# --- Serializador para Nivel de Stock por Almacén ---
class StockLevelReportSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID del Producto.")
    nombre = serializers.CharField(max_length=255, help_text="Nombre del Producto.")
    stock_actual = serializers.IntegerField(help_text="Stock disponible actualmente.")
    almacen_nombre = serializers.CharField(max_length=255, help_text="Nombre del Almacén.")
    empresa_nombre = serializers.CharField(max_length=255, help_text="Nombre de la Empresa.")
    # Si tu modelo Producto tiene un campo stock_minimo, puedes añadirlo aquí:
    # stock_minimo = serializers.IntegerField(required=False, help_text="Stock mínimo recomendado.")

# --- NUEVO: Serializador para Rendimiento de Clientes ---
class ClientPerformanceReportSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID del Cliente.")
    nombre_cliente = serializers.CharField(max_length=255, help_text="Nombre completo del Cliente.")
    email_cliente = serializers.CharField(max_length=255, help_text="Correo electrónico del Cliente.")
    monto_total_comprado = serializers.DecimalField(max_digits=15, decimal_places=2, help_text="Monto total comprado por el cliente.")
    numero_ventas_realizadas = serializers.IntegerField(help_text="Número total de ventas realizadas por el cliente.")