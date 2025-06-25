from django.db import models
from apps.empresas.models import Empresa # Importa el modelo Empresa

class Sucursal(models.Model):

    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Sucursal")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE, # Si la empresa se elimina, sus sucursales también
        related_name='sucursales', # Permite acceder a las sucursales desde una empresa (ej: empresa.sucursales.all())
        verbose_name="Empresa"
    )

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['nombre'] # Ordenar por nombre por defecto
        # Aseguramos que el nombre de la sucursal sea único DENTRO DE CADA EMPRESA
        unique_together = [['nombre', 'empresa']]

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

