from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response  # Necesitarás Response para manejar errores o respuestas específicas
from rest_framework import viewsets, permissions, status, generics
from .models import Empresa
from .serializers import EmpresaSerializer,EmpresaMarketplaceSerializer


class EmpresaPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Empresas.
    - Superusuarios: Acceso total a todas las empresas.
    - Administradores de Empresa: Solo pueden ver/actualizar SU propia empresa.
    - Otros usuarios autenticados: Solo pueden ver SU propia empresa.
    """

    def has_permission(self, request, view):
        # 1. Verificar si el usuario está autenticado. Si no, denegar inmediatamente.
        if not request.user or request.user.is_anonymous:  # Usar is_anonymous es más claro para no autenticados
            return False

        # 2. Si es superusuario, siempre tiene permiso en el nivel de vista.
        # Un superusuario puede listar todas las empresas y crear nuevas.
        if request.user.is_superuser:
            return True

        # 3. Para usuarios no superusuarios (Admin, Empleado, Cliente),
        # solo se les permite interactuar con su propia empresa.
        # No se les permite listar TODAS las empresas ('list' action) ni crear nuevas empresas ('create' action) desde aquí.
        # Esto es crucial: si no son superusuarios, la vista de listado/creación se les deniega aquí.
        if view.action in ['list', 'create']:
            raise PermissionDenied("Solo los superusuarios pueden listar todas las empresas o crear nuevas.")

        # Para 'retrieve', 'update', 'partial_update', 'destroy', el permiso se verificará en has_object_permission.
        # Si llegamos aquí para estas acciones, el usuario está autenticado,
        # la verificación real del objeto se hace a continuación.
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        # 2. Verificar que el usuario está autenticado y tiene una empresa asociada.
        # Además, el objeto de empresa (`obj`) debe ser la empresa del usuario.
        if request.user.is_authenticated and \
                hasattr(request.user, 'empresa') and request.user.empresa is not None and \
                request.user.empresa.pk == obj.pk:  # Comparamos las PKs de las instancias de empresa

            # 3. Verificar el rol del usuario (accediendo a .name)
            if not hasattr(request.user, 'role') or request.user.role is None:
                raise PermissionDenied("Su cuenta no tiene un rol válido asignado.")

            user_role_name = request.user.role.name

            # Métodos seguros (GET): Permitidos para todos los usuarios autenticados de la misma empresa.
            if request.method in permissions.SAFE_METHODS:
                return True

            # Métodos de modificación (PUT/PATCH): Solo permitidos para Administradores de la misma empresa.
            if request.method in ['PUT', 'PATCH'] and user_role_name == 'Administrador':
                return True

            # DELETE: Ningún administrador de empresa puede eliminar la empresa (solo superusuario).
            # Aunque la vista permite DELETE, esta lógica de permiso lo deniega para no-superusuarios.
            if request.method == 'DELETE':
                return False

        return False  # Denegar cualquier otro caso no cubierto explícitamente


class EmpresaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Empresas.
    Proporciona acciones de listado, creación (solo SuperUsuario),
    recuperación, actualización y eliminación (solo SuperUsuario o Admin de su propia empresa).
    """
    serializer_class = EmpresaSerializer
    permission_classes = [EmpresaPermission]
    queryset = Empresa.objects.all() # Aplica tu permiso personalizado

    def get_queryset(self):
        # === INICIO DE LA CORRECCIÓN CRÍTICA PARA SWAGGER/AnonymousUser ===
        # Esta línea es crucial para evitar el AttributeError durante la generación del esquema de drf-yasg.
        if getattr(self, 'swagger_fake_view', False):
            return Empresa.objects.none()
        # === FIN DE LA LA CORRECCIÓN ===

        user = self.request.user
        queryset = Empresa.objects.all()

        if user.is_superuser:
            # Superusuario puede ver todas las empresas.
            return queryset.order_by('nombre')
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            # Usuarios autenticados con una empresa asignada:
            # Solo pueden ver y operar con SU PROPIA empresa.
            # get_queryset filtra la lista para el usuario actual.
            return queryset.filter(pk=user.empresa.pk).order_by('nombre')

        # Si el usuario no es superusuario, no está autenticado, o no tiene empresa asignada,
        # no debe ver ninguna empresa en el listado.
        return Empresa.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    # --- NUEVAS VISTAS PARA EL MARKETPLACE PÚBLICO ---
class MarketplaceEmpresaListView(generics.ListAPIView):
        """
        Vista para listar empresas activas en el marketplace público.
        No requiere autenticación.
        """
        queryset = Empresa.objects.filter(is_active=True).order_by('nombre')
        serializer_class = EmpresaMarketplaceSerializer  # Usamos el serializer más ligero
        permission_classes = []  # ¡IMPORTANTE! Acceso público

class MarketplaceEmpresaDetailView(generics.RetrieveAPIView):
        """
        Vista para ver detalles de una empresa específica en el marketplace público.
        No requiere autenticación.
        """
        queryset = Empresa.objects.filter(is_active=True)
        serializer_class = EmpresaMarketplaceSerializer  # Usamos el serializer más ligero
        lookup_field = 'pk'
        permission_classes = []  # ¡IMPORTANTE! Acceso público