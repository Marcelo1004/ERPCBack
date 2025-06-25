from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters  # Importa filters para SearchFilter
import django_filters.rest_framework  # Importa django_filters backend

from .models import Almacen
from .serializers import AlmacenSerializer
from apps.usuarios.views import IsAdminUserOrSuperUser, IsSuperUser
from .filters import AlmacenFilter  # Importa tu filtro de Almacen


# Permiso personalizado para garantizar la multi-tenencia en Almacenes
class AlmacenPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Almacenes.
    - Superusuarios: Acceso total a todos los almacenes.
    - Administradores de Empresa: Acceso total solo a almacenes de SU propia empresa.
    - Otros usuarios autenticados (CLIENTE, EMPLEADO): Solo lectura de almacenes de SU propia empresa.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Debe estar autenticado para acceder a los almacenes.")

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


class AlmacenListView(generics.ListCreateAPIView):
    """
    Vista para listar todos los almacenes (GET) y crear un nuevo almacén (POST),
    filtrados por la empresa del usuario y con soporte para filtrar por sucursal y búsqueda.
    Ordenado alfabéticamente por nombre.
    """
    serializer_class = AlmacenSerializer
    permission_classes = [AlmacenPermission]

    # --- CAMBIOS AQUÍ para los filtros y ordenamiento ---
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AlmacenFilter  # Asocia tu clase de filtro de Almacen
    search_fields = ['nombre', 'ubicacion', 'sucursal__nombre']  # Campos para la búsqueda general por texto

    # --- FIN CAMBIOS ---

    def get_queryset(self):
        queryset = Almacen.objects.all()

        # Filtrado por empresa basado en el usuario autenticado
        if not self.request.user.is_superuser and self.request.user.is_authenticated and self.request.user.empresa:
            queryset = queryset.filter(empresa=self.request.user.empresa)
        elif not self.request.user.is_authenticated:
            # Si el usuario no está autenticado, no debería ver ningún almacén
            return Almacen.objects.none()

        # Aplica el ordenamiento alfabético por nombre
        return queryset.order_by('nombre').distinct()  # Usar distinct para evitar duplicados si hay joins complejos

    def perform_create(self, serializer):
        # Al crear un almacén, asigna automáticamente la empresa del usuario autenticado
        if not self.request.user.is_superuser:
            if not self.request.user.empresa:
                raise PermissionDenied("No estás asociado a ninguna empresa para crear almacenes.")
            serializer.save(empresa=self.request.user.empresa)
        else:
            serializer.save()


class AlmacenDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener detalles (GET), actualizar (PUT/PATCH) y eliminar (DELETE) un almacén específico,
    restringido a la empresa del usuario.
    """
    serializer_class = AlmacenSerializer
    permission_classes = [AlmacenPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        queryset = Almacen.objects.all()
        if self.request.user.is_superuser:
            return queryset
        elif self.request.user.is_authenticated and self.request.user.empresa:
            return queryset.filter(empresa=self.request.user.empresa)
        return Almacen.objects.none()