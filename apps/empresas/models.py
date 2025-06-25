from django.db import models
from apps.suscripciones.models import Suscripcion
from django.conf import settings  # Importar settings para referenciar AUTH_USER_MODEL


class Empresa(models.Model):
    nombre = models.CharField(max_length=255, unique=True, verbose_name="Nombre de la Empresa")
    nit = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="NIT/RUC")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email_contacto = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email de Contacto")
    logo = models.ImageField(upload_to='logos_empresas/', blank=True, null=True, verbose_name="Logo de la Empresa")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")

    suscripcion = models.ForeignKey(
        Suscripcion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empresas',
        verbose_name="Plan de Suscripción"
    )

    admin_empresa = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empresas_administradas',
        verbose_name="Administrador de la Empresa"
    )

    is_active = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nombre']

    def __str__(self):

        return self.nombre