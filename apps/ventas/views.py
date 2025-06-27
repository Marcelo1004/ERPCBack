from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import action # Importar action
from django.db import transaction
from django.db import models

from .models import Venta, DetalleVenta
from .serializers import VentaSerializer, DetalleVentaSerializer
from apps.productos.models import Producto


# --- Permisos Personalizados ---
class IsAdminOrSuperuser(permissions.BasePermission):
    """Permite el acceso solo a administradores o superusuarios."""
    def has_permission(self, request, view):
        # Asegúrate de que request.user.role es un objeto con un atributo 'name'
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or \
                     (hasattr(request.user, 'role') and request.user.role is not None and request.user.role.name == 'Administrador')))


class IsEmployeeOrHigher(permissions.BasePermission):
    """Permite el acceso a empleados, administradores o superusuarios."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or \
                     (hasattr(request.user, 'role') and request.user.role is not None and request.user.role.name in ['Administrador', 'Empleado'])))


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'cancelar_venta']: # Añadir 'cancelar_venta'
            self.permission_classes = [IsAdminOrSuperuser]
        else:  # 'list', 'retrieve' (ver)
            self.permission_classes = [IsEmployeeOrHigher]
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Venta.objects.none()

        user = self.request.user
        if user.is_superuser:
            return Venta.objects.all().prefetch_related('detalles__producto')
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            return Venta.objects.filter(empresa=user.empresa).prefetch_related('detalles__producto')
        return Venta.objects.none()

    def get_serializer_context(self):
        return {'request': self.request}

    # La lógica de STOCK para CREATE y UPDATE se maneja ahora en VentaSerializer.
    # Por lo tanto, no necesitamos perform_create ni perform_update aquí para el stock.
    # Los métodos perform_create y perform_update del ModelViewSet son solo hooks.
    # Si quisieras añadir lógica de negocio *adicional* que no sea de serialización, iría aquí.

    def perform_destroy(self, instance):
        # Lógica para devolver stock al eliminar una venta COMPLETA
        # Esto reemplaza la lógica anterior en DetalleVentaViewSet.perform_destroy para la venta completa.
        with transaction.atomic():
            for detalle in instance.detalles.all():
                producto = detalle.producto
                producto.stock += detalle.cantidad # Devolver stock
                producto.save(update_fields=['stock'])
            instance.delete() # Eliminar la venta

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar_venta(self, request, pk=None):
        """
        Cancela una venta y devuelve el stock de los productos involucrados.
        Endpoint: /api/ventas/{id}/cancelar/
        """
        try:
            venta = self.get_object()
        except Venta.DoesNotExist:
            return Response({"detail": "Venta no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if venta.estado == 'Cancelada':
            return Response({"detail": "La venta ya está cancelada."}, status=status.HTTP_400_BAD_REQUEST)

        # Usar una transacción atómica para asegurar la consistencia
        with transaction.atomic():
            # Cambiar el estado de la venta
            venta.estado = 'Cancelada'
            venta.save(update_fields=['estado'])

            # Devolver el stock de cada producto en los detalles de la venta
            for detalle in venta.detalles.all():
                producto = detalle.producto
                producto.stock += detalle.cantidad
                producto.save(update_fields=['stock'])

        serializer = self.get_serializer(venta)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer
    descuento_aplicado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Porcentaje de descuento aplicado al producto en esta venta."
    )

    @property
    def subtotal(self):
        precio_con_descuento = self.precio_unitario * (1 - self.descuento_aplicado)
        return precio_con_descuento * self.cantidad

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminOrSuperuser]
        else:  # 'list', 'retrieve'
            self.permission_classes = [IsEmployeeOrHigher]
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DetalleVenta.objects.none()

        user = self.request.user
        if user.is_superuser:
            return DetalleVenta.objects.all().select_related('venta', 'producto')
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            # Filtra los detalles de venta por la empresa de la venta a la que pertenecen
            return DetalleVenta.objects.filter(venta__empresa=user.empresa).select_related('venta', 'producto')
        return DetalleVenta.objects.none()

