from django.db import models

class Suscripcion(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Plan")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del Plan")
    cantidad_usuarios_permitidos = models.PositiveIntegerField(
        default=20,
        verbose_name="Cantidad de Usuarios Permitidos"
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio Mensual")

    class Meta:
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
