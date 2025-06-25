# apps/ventas/models.py

from django.db import models
from django.utils import timezone
from apps.usuarios.models import User  # Asume que User está en apps.usuarios
from apps.productos.models import Producto  # Asume que Producto está en apps.productos
from apps.empresas.models import Empresa  # Asume que Empresa está en apps.empresas


class Venta(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ventas')
    # Podrías añadir un cliente si tienes un modelo Cliente: cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='ventas_realizadas')
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Venta")
    monto_total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Monto Total")
    estado = models.CharField(max_length=50, default='Pendiente', verbose_name="Estado de Venta")

    # Otros campos que podrías necesitar:
    # metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    # comentario = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']  # Las ventas más recientes primero

    def __str__(self):
        return f"Venta #{self.id} de {self.empresa.nombre} - {self.monto_total} ({self.estado})"

    def save(self, *args, **kwargs):
        # Actualiza el monto_total basado en los detalles de venta antes de guardar
        # Esto es más seguro hacerlo en un signal post_save de DetalleVenta
        # o cuando se finaliza la venta. Por simplicidad, no lo haré automáticamente aquí.
        super().save(*args, **kwargs)


class DetalleVenta(models.Model):
    """
    Modelo para representar el detalle de cada producto en una venta.
    """
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")

    # Campos calculados, no almacenados en la BD, o actualizados por un signal
    # subtotal = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        unique_together = ('venta', 'producto')  # Un producto solo puede aparecer una vez por venta

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Venta #{self.venta.id}"

    def save(self, *args, **kwargs):
        # Si el precio_unitario no se proporciona, tómalo del producto al momento de añadir
        if not self.precio_unitario and self.producto:
            self.precio_unitario = self.producto.precio  # Asumiendo que Producto tiene un campo 'precio'

        # Opcional: Actualizar stock del producto
        if self.pk:  # Si ya existe, es una actualización
            original_cantidad = DetalleVenta.objects.get(pk=self.pk).cantidad
            delta_cantidad = self.cantidad - original_cantidad
            self.producto.stock -= delta_cantidad
        else:  # Nueva creación
            self.producto.stock -= self.cantidad

        self.producto.save()  # Guarda el stock actualizado del producto
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Al eliminar un detalle, devuelve la cantidad al stock del producto
        self.producto.stock += self.cantidad
        self.producto.save()
        super().delete(*args, **kwargs)