# apps/sucursales/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response  # Necesitarás Response para manejo de errores personalizados

from .models import Sucursal
from .serializers import SucursalSerializer


# Asegúrate de que tu modelo de usuario tenga 'role' y 'empresa' correctamente configurados.
# Si tu modelo de usuario personalizado no tiene 'role' o 'empresa' directamente,
# o si necesitas acceder a ellos de forma diferente (ej. a través de un perfil),
# deberás ajustar la lógica de SucursalPermission y los get_queryset.


class SucursalPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Sucursales.
    - Superusuarios: Acceso total a todas las sucursales.
    - Administradores de Empresa: Acceso total solo a sucursales de SU propia empresa.
    - Otros usuarios autenticados (CLIENTE, EMPLEADO): Solo lectura de sucursales de SU propia empresa.
    """

    def has_permission(self, request, view):
        # 1. Verificar si el usuario está autenticado. Si no, denegar explícitamente.
        # En DRF, request.user es un AnonymousUser si no está autenticado, que no tiene 'is_authenticated' False,
        # pero es útil para diferenciar. is_anonymous es más preciso para AnonymousUser.
        if not request.user or request.user.is_anonymous:
            raise PermissionDenied("Debe estar autenticado para acceder a las sucursales.")

        # 2. Si es superusuario, siempre tiene permiso.
        if request.user.is_superuser:
            return True

        # 3. Verificar que el usuario autenticado tiene un rol válido y empresa asignada.
        # Esto es crucial para evitar AttributeError si el rol o empresa no están bien configurados.
        # Asumiendo que request.user.role es un objeto con un atributo .name
        # y request.user.empresa es un objeto Empresa o None
        if not hasattr(request.user, 'role') or request.user.role is None or \
                not hasattr(request.user, 'empresa') or request.user.empresa is None:
            raise PermissionDenied("Su cuenta no tiene un rol o empresa válidos asignados.")

        user_role_name = request.user.role.name

        # 4. Lógica de permisos basada en el rol y empresa del usuario
        # Administradores de Empresa: Acceso total a sucursales de SU propia empresa.
        if user_role_name == 'Administrador':
            return True

        # Clientes o Empleados: Solo lectura de sucursales de SU propia empresa.
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
        # Y que el objeto (sucursal) pertenece a la misma empresa del usuario.
        if request.user.is_authenticated and \
                hasattr(request.user, 'empresa') and request.user.empresa is not None and \
                request.user.empresa == obj.empresa:  # Comparar la instancia de empresa

            # 3. Lógica de permisos sobre el objeto basada en el rol
            # Métodos seguros (GET): permitidos para Clientes, Empleados y Administradores de la misma empresa.
            if request.method in permissions.SAFE_METHODS:
                return True

            # Otros métodos (PUT/PATCH/DELETE): permitidos solo para Administradores de la misma empresa.
            if hasattr(request.user,
                       'role') and request.user.role is not None and request.user.role.name == 'Administrador':
                return True

        # Denegar cualquier otro caso.
        return False


class SucursalViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Sucursales. Proporciona acciones de listado, creación,
    recuperación, actualización y eliminación.
    """
    serializer_class = SucursalSerializer
    permission_classes = [SucursalPermission]  # Aplica tu permiso personalizado

    def get_queryset(self):
        # === INICIO DE LA CORRECCIÓN CRÍTICA PARA SWAGGER/AnonymousUser ===
        # Esta línea es crucial para evitar el AttributeError durante la generación del esquema.
        # 'swagger_fake_view' es un atributo que drf-yasg añade a la vista durante la introspección.
        if getattr(self, 'swagger_fake_view', False):
            return Sucursal.objects.none()  # Devuelve un QuerySet vacío para drf-yasg
        # === FIN DE LA CORRECCIÓN ===

        user = self.request.user
        queryset = Sucursal.objects.all()

        # El ViewSet llamará a has_permission y has_object_permission primero.
        # Aquí filtramos el queryset para que solo muestre lo que el usuario debería ver en un listado.

        if user.is_superuser:
            return queryset.order_by('nombre')
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            # Usuarios autenticados con empresa: solo pueden ver las sucursales de su propia empresa
            return queryset.filter(empresa=user.empresa).order_by('nombre')

        # Si el usuario no es superusuario ni está asociado a una empresa (o no autenticado),
        # no debe ver ninguna sucursal por defecto en el listado.
        return Sucursal.objects.none()  # Devuelve un QuerySet vacío

    def perform_create(self, serializer):
        # Asigna automáticamente la empresa del usuario que está creando la sucursal
        user = self.request.user
        if not user.is_superuser:
            if not (hasattr(user, 'empresa') and user.empresa):
                # Esto ya debería ser atrapado por has_permission, pero es una doble verificación.
                raise PermissionDenied("No estás asociado a ninguna empresa para crear sucursales.")
            serializer.save(empresa=user.empresa)
        else:
            # Para SuperUsuarios, pueden crear sin una empresa pre-asignada.
            # Se asume que si el superusuario no proporciona 'empresa' en la data,
            # no se asigna (lo cual podría ser un problema si necesitas que siempre tenga una).
            # Si el superusuario debe poder especificar la empresa, el serializer debe manejarlo.
            serializer.save()

    # No necesitas overridear perform_update ni perform_destroy a menos que quieras
    # añadir lógica personalizada que no sea el comportamiento por defecto de DRF.
    # La lógica de filtrado por empresa y permisos se maneja en get_queryset y SucursalPermission.