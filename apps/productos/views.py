# apps/productos/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters  # Importa filters para SearchFilter
import django_filters.rest_framework  # Importa django_filters backend

from .models import Producto
from .serializers import ProductoSerializer
from .filters import ProductoFilter  # Importa tu filtro de Producto

# Nota: Asumo que `erp.permissions.IsAdminOrSuperUser, IsSuperUser`
# no son directamente usadas en la clase ProductoViewSet, ya que ProductoPermission
# maneja toda la lógica. Si estas clases se usan en otros ViewSets,
# asegúrate de que están bien definidas y accesibles.


# Permiso personalizado para garantizar la multi-tenencia en Productos
class ProductoPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Productos.
    - Superusuarios: Acceso total a todos los productos.
    - Administradores de Empresa: Acceso total solo a productos de SU propia empresa.
    - Otros usuarios autenticados (CLIENTE, EMPLEADO): Solo lectura de productos de SU propia empresa.
    """

    def has_permission(self, request, view):
        # 1. Verificar si el usuario está autenticado. Si no, denegar explícitamente.
        if not request.user or request.user.is_anonymous:
            raise PermissionDenied("Debe estar autenticado para acceder a los productos.")

        # 2. Si es superusuario, siempre tiene permiso.
        if request.user.is_superuser:
            return True

        # 3. Verificar que el usuario autenticado tiene un rol válido y empresa asignada.
        # Esto es crucial para evitar AttributeError si el rol o empresa no están bien configurados.
        if not hasattr(request.user, 'role') or request.user.role is None or \
           not hasattr(request.user, 'empresa') or request.user.empresa is None:
            raise PermissionDenied("Su cuenta no tiene un rol o empresa válidos asignados.")

        user_role_name = request.user.role.name

        # 4. Lógica de permisos basada en el rol y empresa del usuario
        # Administradores de Empresa: Acceso total a productos de SU propia empresa.
        if user_role_name == 'Administrador':
            return True

        # Clientes o Empleados: Solo lectura de productos de SU propia empresa.
        if user_role_name in ['Cliente', 'Empleado'] and request.method in permissions.SAFE_METHODS:
            return True

        # Para cualquier otro caso (ej. intentar POST/PUT/DELETE siendo Cliente/Empleado,
        # o un rol no reconocido) denegar.
        return False

    def has_object_permission(self, request, view, obj):
        # 1. Si es superusuario, siempre tiene permiso sobre el objeto.
        if request.user.is_superuser:
            return True

        # 2. Verificar que el usuario está autenticado y tiene una empresa asociada.
        # Y que el objeto (producto) pertenece a la misma empresa del usuario.
        if request.user.is_authenticated and \
           hasattr(request.user, 'empresa') and request.user.empresa is not None and \
           request.user.empresa == obj.empresa:  # Comparar la instancia de empresa

            # 3. Lógica de permisos sobre el objeto basada en el rol
            # Métodos seguros (GET): permitidos para Clientes, Empleados y Administradores de la misma empresa.
            if request.method in permissions.SAFE_METHODS:
                return True

            # Otros métodos (PUT/PATCH/DELETE): permitidos solo para Administradores de la misma empresa.
            if hasattr(request.user, 'role') and request.user.role is not None and request.user.role.name == 'Administrador':
                return True

        # Denegar cualquier otro caso.
        return False


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Productos. Proporciona acciones de listado, creación,
    recuperación, actualización y eliminación, con soporte para filtrado y búsqueda.
    """
    serializer_class = ProductoSerializer
    permission_classes = [ProductoPermission] # Aplica tu permiso personalizado

    filter_backends = [filters.SearchFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ProductoFilter
    search_fields = [
        'nombre',
        'descripcion',
        'categoria__nombre',
        'almacen__nombre',
        'almacen__sucursal__nombre',
    ]

    def get_queryset(self):

        if getattr(self, 'swagger_fake_view', False):
            return Producto.objects.none()


        user = self.request.user
        queryset = Producto.objects.all()

        if user.is_superuser:
            return queryset.distinct().order_by('nombre') # Añade .order_by('nombre') para consistencia y paginación
            # Es crucial verificar is_authenticated y la existencia de 'empresa' para evitar AttributeError.
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            return queryset.filter(empresa=user.empresa).distinct().order_by('nombre')


        return Producto.objects.none()

    def perform_create(self, serializer):
        # Al crear un producto, asigna automáticamente la empresa del usuario autenticado
        user = self.request.user
        if not user.is_superuser:
            # Verificar que el usuario que crea tiene una empresa válida
            if not (hasattr(user, 'empresa') and user.empresa):
                raise PermissionDenied("No estás asociado a ninguna empresa para crear productos.")
            serializer.save(empresa=user.empresa)
        else:
            serializer.save()

    def get_serializer_class(self):

        serializer_class = super().get_serializer_class()
        print(f"\n--- DEBUG: ProductoViewSet está usando el serializer: {serializer_class.__name__} ---")
        return serializer_class

    def get_queryset(self):
        print("\n--- DEBUG: get_queryset de ProductoViewSet llamado ---")

        if getattr(self, 'swagger_fake_view', False):
            print("--- DEBUG: Modo Swagger_fake_view activado, retornando queryset vacío. ---")
            return Producto.objects.none()
    # No necesitas overridear perform_update ni perform_destroy aquí.