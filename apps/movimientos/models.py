from django.db import models
from django.utils import timezone
from apps.proveedores.models import Proveedor
from apps.productos.models import Producto # Asume que Producto está en apps.productos
from apps.almacenes.models import Almacen # Asume que Almacen está en apps.almacenes
from apps.empresas.models import Empresa # Asume que Empresa está en apps.empresas

class Movimiento(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
    ]

    # Relaciones principales
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_suministrados')
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_recibidos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Información del movimiento
    fecha_llegada = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Llegada")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    costo_transporte = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo de Transporte")
    monto_total_operacion = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Monto Total de la Operación")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Pendiente',  # O el estado inicial que prefieras
        help_text="Estado actual del movimiento (Pendiente, Aceptado, Rechazado)"
    )
    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha_llegada'] # Los más recientes primero

    def __str__(self):
        return f"Movimiento #{self.id} de {self.proveedor.nombre if self.proveedor else 'N/A'} a {self.almacen_destino.nombre if self.almacen_destino else 'N/A'}"

    def save(self, *args, **kwargs):
        # Asegurarse de que el monto_total_operacion se recalcula antes de guardar
        # Esto lo haremos en el serializer para mayor control transaccional
        super().save(*args, **kwargs)

class DetalleMovimiento(models.Model):
    movimiento = models.ForeignKey(Movimiento, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad_suministrada = models.PositiveIntegerField(verbose_name="Cantidad Suministrada")
    colores = models.CharField(max_length=200, blank=True, null=True, verbose_name="Colores Suministrados (ej. Rojo, Azul)") # Opcional, puedes cambiar el tipo si es más complejo
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Unitario de Compra")
    valor_total_producto = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Valor Total del Producto")

    class Meta:
        verbose_name = "Detalle de Movimiento"
        verbose_name_plural = "Detalles de Movimiento"
        unique_together = ('movimiento', 'producto') # Un producto solo puede aparecer una vez por movimiento

    def __str__(self):
        return f"{self.cantidad_suministrada} x {self.producto.nombre} en Movimiento #{self.movimiento.id}"

    def save(self, *args, **kwargs):
        # Calcular valor_total_producto antes de guardar
        self.valor_total_producto = self.cantidad_suministrada * self.valor_unitario
        super().save(*args, **kwargs)