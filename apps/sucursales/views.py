from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied

from .models import Sucursal
from .serializers import SucursalSerializer
from apps.usuarios.views import IsAdminUserOrSuperUser, IsSuperUser


class SucursalPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Sucursales.
    - Superusuarios: Acceso total a todas las sucursales.
    - Administradores de Empresa: Acceso total solo a sucursales de SU propia empresa.
    - Otros usuarios autenticados (CLIENTE, EMPLEADO): Solo lectura de sucursales de SU propia empresa.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Debe estar autenticado para acceder a las sucursales.")

        if request.user.is_superuser:
            return True

        if request.user.role == 'ADMINISTRATIVO' and request.user.empresa:
            return True

        if request.user.role in ['CLIENTE', 'EMPLEADO'] and request.user.empresa and request.method == 'GET':
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if request.user.is_authenticated and request.user.empresa == obj.empresa:
            if request.method in permissions.SAFE_METHODS:  # GET
                return True
            if request.user.role == 'ADMINISTRATIVO':
                return True

        return False


class SucursalListView(generics.ListCreateAPIView):
    """
    Vista para listar todas las sucursales (GET) y crear una nueva sucursal (POST),
    filtradas por la empresa del usuario y ordenadas alfabéticamente por nombre.
    """
    serializer_class = SucursalSerializer
    permission_classes = [SucursalPermission]

    def get_queryset(self):
        queryset = Sucursal.objects.all()
        if self.request.user.is_superuser:
            return queryset.order_by('nombre') # ORDEN ALFABÉTICO
        elif self.request.user.is_authenticated and self.request.user.empresa:
            return queryset.filter(empresa=self.request.user.empresa).order_by('nombre') # ORDEN ALFABÉTICO
        return Sucursal.objects.none()

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            if not self.request.user.empresa:
                raise PermissionDenied("No estás asociado a ninguna empresa para crear sucursales.")
            serializer.save(empresa=self.request.user.empresa)
        else:
            serializer.save()


class SucursalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener detalles (GET), actualizar (PUT/PATCH) y eliminar (DELETE) una sucursal específica,
    restringido a la empresa del usuario.
    """
    serializer_class = SucursalSerializer
    permission_classes = [SucursalPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        queryset = Sucursal.objects.all()
        if self.request.user.is_superuser:
            return queryset
        elif self.request.user.is_authenticated and self.request.user.empresa:
            return queryset.filter(empresa=self.request.user.empresa)
        return Sucursal.objects.none()