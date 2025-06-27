# apps/logs/views.py

from rest_framework import viewsets, permissions
from .models import ActividadLog
from .serializers import ActividadLogSerializer

# --- Permisos Personalizados ---
class IsAdminOrSuperuser(permissions.BasePermission):
    """Permite el acceso solo a administradores o superusuarios."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or \
                    (hasattr(request.user, 'role') and request.user.role is not None and request.user.role.name == 'Administrador'))) # Asumiendo role.name es el atributo a comparar y el nombre es 'Administrador'


class ActividadLogViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly para logs
    queryset = ActividadLog.objects.all()
    serializer_class = ActividadLogSerializer
    permission_classes = [IsAdminOrSuperuser] # Solo admins/superusers pueden ver logs

    def get_queryset(self):
        """Filtra logs por empresa del usuario si no es superusuario."""
        if getattr(self, 'swagger_fake_view', False):
            return ActividadLog.objects.none() # Devuelve un QuerySet vacío para drf-yasg

        user = self.request.user
        if user.is_superuser:
            return ActividadLog.objects.all()
        # Verificar si el usuario está autenticado y si tiene el atributo 'empresa'
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            return ActividadLog.objects.filter(empresa=user.empresa)
        return ActividadLog.objects.none()