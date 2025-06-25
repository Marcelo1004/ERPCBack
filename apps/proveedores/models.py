# apps/compras_proveedores/models.py

from django.db import models
from apps.empresas.models import Empresa  # Asegúrate de que esta importación sea correcta

class Proveedor(models.Model):
    """
    Modelo para registrar los proveedores del sistema.
    Asociado a una Empresa para multi-tenancy.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='proveedores', null=False, blank=False)
    nombre = models.CharField(max_length=100) # No unique a nivel global, sino por empresa
    contacto_nombre = models.CharField(max_length=100, blank=True, null=True)
    contacto_email = models.EmailField(max_length=100, blank=True, null=True)
    contacto_telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    nit = models.CharField(max_length=20, blank=True, null=True, verbose_name="NIT/RUC")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        # Restricción única para nombre y empresa
        unique_together = ('empresa', 'nombre',)
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

# No añadimos los modelos de Compra/DetalleCompra aún, nos centraremos solo en Proveedor por ahora.