from django.db import models
from apps.empresas.models import Empresa # Importa el modelo Empresa

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Categoría")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE, # Si la empresa se elimina, sus categorías también
        related_name='categorias', # Permite acceder a las categorías desde una empresa
        verbose_name="Empresa"
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre'] # Ordenar por nombre por defecto
        # Aseguramos que el nombre de la categoría sea único DENTRO DE CADA EMPRESA
        unique_together = [['nombre', 'empresa']]

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

