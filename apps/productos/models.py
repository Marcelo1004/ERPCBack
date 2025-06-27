from django.db import models
from apps.categorias.models import Categoria # Asumiendo que Categoria está en apps/categorias
from apps.almacenes.models import Almacen   # Asumiendo que Almacen está en apps/almacenes
from apps.empresas.models import Empresa   # Importa el modelo Empresa
from decimal import Decimal
class Producto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Producto")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock Disponible")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen del Producto")
    descuento = models.DecimalField(
        max_digits=5,
        decimal_places=4,  # <--- ¡CAMBIA ESTO DE 2 A 4!
        default=Decimal('0.0000'),  # <--- ¡CAMBIA ESTO PARA USAR DECIMAL Y 4 DECIMALES!
        help_text="Porcentaje de descuento (ej. 0.10 para 10%). Máximo 1.00 (100%)."
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name="Categoría"
    )

    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name="Almacén"
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE, # Si la empresa se elimina, sus productos también
        related_name='productos', # Permite acceder a los productos desde una empresa
        verbose_name="Empresa"
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']
        unique_together = [['nombre', 'almacen', 'empresa']]

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"


    def save(self, *args, **kwargs):
        # Asegurarse de que el descuento no exceda 1.00 (100%) y no sea menor que 0
        if self.descuento is None:
            self.descuento = Decimal('0.0000') # Default si es None
        if self.descuento > Decimal('1.0000'):
            self.descuento = Decimal('1.0000')
        elif self.descuento < Decimal('0.0000'):
            self.descuento = Decimal('0.0000')
        super().save(*args, **kwargs)

