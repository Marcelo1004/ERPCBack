# apps/ventas/admin.py

from django.contrib import admin
from .models import Venta, DetalleVenta

# Puedes crear un inline para ver los detalles de venta directamente en la vista de Venta
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1 # Número de formularios vacíos para añadir detalles
    raw_id_fields = ['producto'] # Facilita la selección de productos si hay muchos

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'empresa', 'usuario', 'fecha', 'monto_total', 'estado']
    list_filter = ['estado', 'empresa', 'fecha']
    search_fields = ['id', 'empresa__nombre', 'usuario__username']
    inlines = [DetalleVentaInline] # Muestra los detalles directamente en la venta
    readonly_fields = ['monto_total'] # Para que no se edite manualmente, se calcularía

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ['venta', 'producto', 'cantidad', 'precio_unitario']
    list_filter = ['venta__empresa', 'producto__categoria']
    search_fields = ['venta__id', 'producto__nombre']
    raw_id_fields = ['venta', 'producto']