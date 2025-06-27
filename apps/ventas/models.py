# apps/ventas/models.py

from django.db import models
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Case, When
from django.db import transaction

# Asegúrate de que estas importaciones sean correctas para tu proyecto
from apps.usuarios.models import CustomUser
from apps.empresas.models import Empresa
from apps.productos.models import Producto


class Venta(models.Model):
    """
    Modelo para representar una venta en el sistema ERP.
    """
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Completada', 'Completada'),
        ('Cancelada', 'Cancelada'),
    ]

    ORIGEN_CHOICES = [ # <-- ¡NUEVO! Campo para el origen de la venta
        ('MANUAL', 'Manual'),
        ('MARKETPLACE', 'Marketplace'),
    ]

    fecha = models.DateTimeField(auto_now_add=True, help_text="Fecha y hora de creación de la venta.")
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                      help_text="Monto total de la venta después de descuentos.")
    usuario = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas_realizadas',
        help_text="Usuario que realizó la compra (cliente o vendedor)."
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='ventas_empresa',
        help_text="Empresa a la que pertenece esta venta."
    )
    estado = models.CharField(
        max_length=50,
        choices=ESTADO_CHOICES,
        default='Pendiente',
        help_text="Estado actual de la venta (Pendiente, Completada, Cancelada)."
    )
    origen = models.CharField( # <-- ¡NUEVO CAMPO ORIGEN!
        max_length=50,
        choices=ORIGEN_CHOICES,
        default='MANUAL', # Por defecto es manual si se crea desde el ERP
        help_text="Origen de la venta (Manual, Marketplace)."
    )

    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha'] # Ordenar por fecha de venta descendente

    def __str__(self):
        return f"Venta #{self.id} - {self.empresa.nombre} - ${self.monto_total}"

    def calculate_total_amount(self):
        """
        Calcula el monto total de la venta sumando los subtotales de sus detalles
        aplicando los descuentos.
        """
        total = self.detalles.annotate(
            subtotal_item=ExpressionWrapper(
                F('cantidad') * F('precio_unitario') * (1 - F('descuento_aplicado')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).aggregate(
            total_sum=Sum('subtotal_item')
        )['total_sum']
        return total if total is not None else Decimal('0.00')

    def cancel_sale_and_restore_stock(self):
        """
        Cancela la venta y revierte el stock de los productos.
        """
        if self.estado == 'Cancelada':
            return # Ya está cancelada, no hacer nada

        with transaction.atomic():
            for detalle in self.detalles.all():
                producto = detalle.producto
                producto.stock += detalle.cantidad
                producto.save()
            self.estado = 'Cancelada'
            self.save(update_fields=['estado'])


class DetalleVenta(models.Model):
    """
    Modelo para los detalles de una venta, es decir, los productos individuales en una venta.
    """
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_venta') # PROTECT para evitar eliminar producto si está en ventas
    cantidad = models.IntegerField(help_text="Cantidad del producto vendido.")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2,
                                          help_text="Precio unitario del producto al momento de la venta.")
    descuento_aplicado = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000,
                                             help_text="Descuento aplicado por unidad (ej. 0.10 para 10%).")

    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        unique_together = ('venta', 'producto') # Un producto solo puede aparecer una vez por venta

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Venta #{self.venta.id}"

    @property
    def subtotal_item(self):
        """Calcula el subtotal para este detalle de venta."""
        return self.cantidad * self.precio_unitario * (1 - self.descuento_aplicado)

    def save(self, *args, **kwargs):
        """
        Cuando se guarda un detalle de venta, actualiza el stock del producto
        y recalcula el monto total de la venta.
        """
        is_new = self._state.adding
        old_cantidad = 0

        if not is_new:
            try:
                # Recuperar la cantidad anterior si el detalle ya existía
                old_cantidad = DetalleVenta.objects.get(pk=self.pk).cantidad
            except DetalleVenta.DoesNotExist:
                pass # Esto no debería pasar en una actualización normal

        super().save(*args, **kwargs)

        # Si es un nuevo detalle o la cantidad ha cambiado, ajustar stock
        if is_new or self.cantidad != old_cantidad:
            stock_change = self.cantidad - old_cantidad
            self.producto.stock -= stock_change
            self.producto.save(update_fields=['stock'])

        # Recalcular el monto total de la venta padre
        self.venta.monto_total = self.venta.calculate_total_amount()
        self.venta.save(update_fields=['monto_total'])

    def delete(self, *args, **kwargs):
        """
        Cuando se elimina un detalle de venta, restaura el stock del producto
        y recalcula el monto total de la venta.
        """
        # Restaurar stock antes de eliminar el detalle
        self.producto.stock += self.cantidad
        self.producto.save(update_fields=['stock'])

        super().delete(*args, **kwargs)

        # Recalcular el monto total de la venta padre
        self.venta.monto_total = self.venta.calculate_total_amount()
        self.venta.save(update_fields=['monto_total'])

