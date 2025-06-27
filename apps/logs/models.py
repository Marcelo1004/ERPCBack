# apps/logs/models.py

from django.db import models
from django.utils import timezone
from apps.usuarios.models import CustomUser   # Asume que User está en apps.usuarios
from apps.empresas.models import Empresa  # Asume que Empresa está en apps.empresas


class ActividadLog(models.Model):
    """
    Modelo para registrar actividades importantes en el sistema.
    """
    user = models.ForeignKey(CustomUser , on_delete=models.SET_NULL, null=True, blank=True, related_name='actividades')
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='actividades')

    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora")
    activity_type = models.CharField(max_length=100, verbose_name="Tipo de Actividad")
    description = models.TextField(verbose_name="Descripción")

    # Campos opcionales para mayor detalle
    entity_id = models.IntegerField(null=True, blank=True, verbose_name="ID de Entidad Afectada")
    entity_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre de Entidad Afectada")

    # Si quieres almacenar datos JSON adicionales del evento
    # extra_data = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de Actividad"
        verbose_name_plural = "Registros de Actividad"
        ordering = ['-timestamp']  # Las más recientes primero

    def __str__(self):
        user_info = f" por {self.user.username}" if self.user else ""
        empresa_info = f" en {self.empresa.nombre}" if self.empresa else ""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.activity_type}: {self.description}{user_info}{empresa_info}"