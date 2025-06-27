from django.db import models
from django.utils import timezone
from apps.usuarios.models import CustomUser
from apps.productos.models import Producto
from apps.empresas.models import Empresa
from decimal import Decimal

class Venta(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ventas')
    usuario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='ventas_realizadas')
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Venta")
    monto_total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Monto Total")
    estado = models.CharField(max_length=50, default='Pendiente', verbose_name="Estado de Venta") # Pendiente, Completada, Cancelada

    def calculate_total_amount(self):
        """
        Calculates the total amount of the sale based on its associated
        DetalleVenta instances.
        """
        total = 0
        # Assuming your DetalleVenta model has a ForeignKey to Venta
        # with a related_name (e.g., 'detalles').
        # If not specified, Django creates '_set' (e.g., detalleventa_set).
        # Adjust 'detalles' to your actual related_name or '_set'
        for detalle in self.detalles.all():
            # Ensure 'cantidad' and 'precio_unitario' match your DetalleVenta fields
            total += detalle.cantidad * detalle.precio_unitario
        return total

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure monto_total is calculated
        before saving, especially for new sales or when details change.
        Note: For existing sales where details are added/updated independently,
        you might need to call calculate_total_amount explicitly or use signals.
        However, for updates through the serializer, the serializer's
        `update` method will handle it.
        """
        # It's usually better to calculate this in the serializer's create/update
        # or through signals to avoid recalculating on every save,
        # especially if details are added/modified separately.
        # However, if you want it to be calculated on every save of the Venta,
        # you can uncomment the line below.
        # self.monto_total = self.calculate_total_amount()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']

    def __str__(self):
        return f"Venta #{self.id} de {self.empresa.nombre} - {self.monto_total} ({self.estado})"


class DetalleVenta(models.Model):
    venta = models.ForeignKey('Venta', related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey('productos.Producto', on_delete=models.CASCADE)
    cantidad = models.IntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")
    descuento_aplicado = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'), verbose_name="Descuento Aplicado")

    # Propiedad para calcular el subtotal de este detalle
    @property
    def subtotal(self):
        # Asegúrate de aplicar el descuento si lo tienes en cuenta en el monto final
        # Por ejemplo, si el descuento_aplicado es 0.10 (10%), se paga el 90%
        return (self.cantidad * self.precio_unitario) * (Decimal('1.00') - self.descuento_aplicado)

    def save(self, *args, **kwargs):
        if not self.precio_unitario and self.producto:
            self.precio_unitario = self.producto.precio # Asegúrate de que 'precio' es el nombre correcto del campo en tu modelo Producto
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Venta #{self.venta.id}"

