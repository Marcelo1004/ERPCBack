# apps/pagos/models.py

from django.db import models
from django.utils import timezone
from apps.ventas.models import Venta  # Asume que Venta está en apps.ventas.models
from apps.usuarios.models import CustomUser  # Asume que CustomUser está en apps.usuarios.models
from apps.empresas.models import Empresa  # Asume que Empresa está en apps.empresas.models
from decimal import Decimal  # Necesario para manejar DecimalFields


class Pago(models.Model):
    """
    Modelo para registrar pagos asociados a ventas u otros conceptos.
    """
    METODO_PAGO_CHOICES = [
        ('STRIPE', 'Stripe'),
        ('QR', 'QR (Código QR)'),
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
    ]

    ESTADO_PAGO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADO', 'Completado'),
        ('FALLIDO', 'Fallido'),
        # Eliminado 'REEMBOLSADO' según tu nueva definición
    ]

    # Relación OneToOne con la Venta
    # Esto significa que una Venta puede tener como máximo un Pago asociado, y viceversa.
    venta = models.OneToOneField(
        Venta,
        on_delete=models.SET_NULL,  # Si la venta se elimina, el pago puede quedar, pero el enlace se borra
        null=True,
        blank=True,
        related_name='pago',  # Cambiado a 'pago' (singular) para OneToOneField
        help_text="Venta asociada a este pago."
    )

    # Cliente que realizó el pago
    cliente = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,  # No queremos borrar un usuario si tiene pagos
        related_name='pagos_realizados',
        help_text="Cliente que realizó el pago."
    )

    # Empresa que recibe el pago (o a la que pertenece la venta)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,  # No queremos borrar una empresa si tiene pagos
        related_name='pagos_recibidos',
        help_text="Empresa que recibe este pago."
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto total del pago."
    )
    fecha_pago = models.DateTimeField(
        default=timezone.now,
        # Usar default=timezone.now en lugar de auto_now_add para permitir edición de fecha si es necesario
        help_text="Fecha y hora en que se registró el pago."
    )
    metodo_pago = models.CharField(
        max_length=50,
        choices=METODO_PAGO_CHOICES,
        default='STRIPE',
        help_text="Método de pago utilizado (ej. Stripe, QR)."
    )
    referencia_transaccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID o referencia de la transacción de la pasarela de pago."
    )
    estado_pago = models.CharField(
        max_length=50,
        choices=ESTADO_PAGO_CHOICES,
        default='COMPLETADO',  # Valor por defecto actualizado
        help_text="Estado actual del pago (ej. Pendiente, Completado, Fallido)."
    )

    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago']  # Ordenar por fecha de pago descendente

    def __str__(self):
        # El __str__ reflejado desde tu último input
        return f"Pago #{self.id} de ${self.monto} - Venta: {self.venta.id if self.venta else 'N/A'}"

    def save(self, *args, **kwargs):
        # Asegurarse de que el monto sea siempre positivo
        if self.monto < 0:
            self.monto = Decimal('0.00')  # O lanzar un error de validación
        super().save(*args, **kwargs)

