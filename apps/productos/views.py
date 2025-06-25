import django_filters
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters  # Importa filters para SearchFilter

from .models import Producto
from .serializers import ProductoSerializer
from apps.usuarios.views import IsAdminUserOrSuperUser, IsSuperUser
from .filters import ProductoFilter  # Importa tu filtro de Producto


# Permiso personalizado para garantizar la multi-tenencia en Productos
class ProductoPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Productos.
    - Superusuarios: Acceso total a todos los productos.
    - Administradores de Empresa: Acceso total solo a productos de SU propia empresa.
    - Otros usuarios autenticados (CLIENTE, EMPLEADO): Solo lectura de productos de SU propia empresa.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Debe estar autenticado para acceder a los productos.")

        if request.user.is_superuser:
            return True

        if request.user.role == 'ADMINISTRATIVO' and request.user.empresa:
            return True

        # Permitir GET para CLIENTE/EMPLEADO solo si están asociados a una empresa
        if request.user.role in ['CLIENTE',
                                 'EMPLEADO'] and request.user.empresa and request.method in permissions.SAFE_METHODS:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if request.user.is_authenticated and request.user.empresa == obj.empresa:
            if request.method in permissions.SAFE_METHODS:  # GET
                return True
            if request.user.role == 'ADMINISTRATIVO':  # Admin de empresa puede CUD
                return True

        return False


class ProductoListView(generics.ListCreateAPIView):
    """
    Vista para listar todos los productos (GET) y crear un nuevo producto (POST),
    filtrados por la empresa del usuario y ahora con soporte para búsqueda y categoría.
    """
    serializer_class = ProductoSerializer
    permission_classes = [ProductoPermission]

    # --- CAMBIOS AQUÍ para los filtros ---
    filter_backends = [filters.SearchFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ProductoFilter  # Asocia tu clase de filtro de django-filter
    search_fields = [
        'nombre',  # Búsqueda por nombre de producto
        'descripcion',  # Búsqueda por descripción de producto
        'categoria__nombre',  # Búsqueda por nombre de categoría relacionada
        'almacen__nombre',  # Búsqueda por nombre de almacén relacionado
        'almacen__sucursal__nombre',  # Búsqueda por nombre de sucursal relacionada al almacén
    ]

    # --- FIN CAMBIOS ---

    def get_queryset(self):
        queryset = Producto.objects.all()

        # Filtrado por empresa basado en el usuario autenticado
        if not self.request.user.is_superuser and self.request.user.is_authenticated and self.request.user.empresa:
            queryset = queryset.filter(empresa=self.request.user.empresa)
        elif not self.request.user.is_authenticated:
            # Si el usuario no está autenticado, no debería ver ningún producto
            return Producto.objects.none()

        # Los filtros de SearchFilter y DjangoFilterBackend se aplican automáticamente
        # al queryset devuelto por get_queryset.

        return queryset.distinct()  # Usar distinct para evitar duplicados si hay joins complejos

    def perform_create(self, serializer):
        # Al crear un producto, asigna automáticamente la empresa del usuario autenticado
        if not self.request.user.is_superuser:
            if not self.request.user.empresa:
                raise PermissionDenied("No estás asociado a ninguna empresa para crear productos.")
            serializer.save(empresa=self.request.user.empresa)
        else:
            # Si es SuperUsuario, espera que la empresa se proporcione en la data
            # O, si no se proporciona, podrías asignar una por defecto o lanzar un error
            # Si permites que el superusuario cree productos sin empresa, déjalo así.
            # Si es requerido, añade validación aquí.
            serializer.save()


class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener detalles (GET), actualizar (PUT/PATCH) y eliminar (DELETE) un producto específico,
    restringido a la empresa del usuario.
    """
    serializer_class = ProductoSerializer
    permission_classes = [ProductoPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        # El queryset base es el mismo que en ListCreateAPIView
        queryset = Producto.objects.all()
        if not self.request.user.is_superuser and self.request.user.is_authenticated and self.request.user.empresa:
            queryset = queryset.filter(empresa=self.request.user.empresa)
        elif not self.request.user.is_authenticated:
            return Producto.objects.none()
        return queryset