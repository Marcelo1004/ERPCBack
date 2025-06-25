from django.db import models
from apps.sucursales.models import Sucursal # Importa el modelo Sucursal
from apps.empresas.models import Empresa   # Importa el modelo Empresa

class Almacen(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Almacén")
    ubicacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación")
    capacidad = models.IntegerField(null=True, blank=True, verbose_name="Capacidad (m³ o unidades)")

    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='almacenes',
        verbose_name="Sucursal Asociada"
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE, # Si la empresa se elimina, sus almacenes también
        related_name='almacenes', # Permite acceder a los almacenes desde una empresa
        verbose_name="Empresa"
    )

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ['nombre'] # Ordenar por nombre por defecto
        # Aseguramos que el nombre del almacén sea único DENTRO DE CADA EMPRESA
        unique_together = [['nombre', 'empresa']]

    def __str__(self):
        """
        Representación en cadena del objeto Almacen.
        """
        return f"{self.nombre} ({self.empresa.nombre})"

