# apps/ventas/views.py (Fragmento - solo VentaViewSet)

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db import transaction

from .models import Venta, DetalleVenta
from .serializers import VentaSerializer, DetalleVentaSerializer
from apps.productos.models import Producto # Para verificar stock

# --- Permisos Personalizados ---
class IsAdminOrSuperuser(permissions.BasePermission):
    """Permite el acceso solo a administradores o superusuarios."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or request.user.role == 'ADMINISTRATIVO'))

class IsEmployeeOrHigher(permissions.BasePermission):
    """Permite el acceso a empleados, administradores o superusuarios."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or request.user.role in ['ADMINISTRATIVO', 'EMPLEADO']))

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminOrSuperuser]
        else: # 'list', 'retrieve' (ver)
            self.permission_classes = [IsEmployeeOrHigher]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Venta.objects.all().prefetch_related('detalles__producto') # Pre-carga detalles y productos
        elif user.empresa:
            return Venta.objects.filter(empresa=user.empresa).prefetch_related('detalles__producto')
        return Venta.objects.none()

    def get_serializer_context(self):
        # Pasa el objeto request al serializador para que pueda acceder a request.user
        return {'request': self.request}

    # Ya no necesitamos perform_create para asignar usuario/empresa,
    # el serializer se encarga de eso en su método create.
    # removemos la sobrescritura de perform_create aquí

    # Puedes añadir lógica personalizada para update/destroy si es necesario,
    # por ejemplo, para manejar reversión de stock en caso de anulación.


class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminOrSuperuser]
        else: # 'list', 'retrieve'
            self.permission_classes = [IsEmployeeOrHigher]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DetalleVenta.objects.all().select_related('venta', 'producto')
        elif user.empresa:
            return DetalleVenta.objects.filter(venta__empresa=user.empresa).select_related('venta', 'producto')
        return DetalleVenta.objects.none()

    def perform_create(self, serializer):
        # La validación de stock se moverá al serializer para reusabilidad
        serializer.save()

    def perform_update(self, serializer):
        # La lógica de stock se moverá al serializer
        serializer.save()

    def perform_destroy(self, instance):
        # El método delete del modelo DetalleVenta ya manejará la reversión del stock
        instance.delete()