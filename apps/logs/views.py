# apps/logs/views.py

from rest_framework import viewsets, permissions
from .models import ActividadLog
from .serializers import ActividadLogSerializer

# --- Permisos Personalizados (reutilizados o definidos si no existen) ---
class IsAdminOrSuperuser(permissions.BasePermission):
    """Permite el acceso solo a administradores o superusuarios."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                    (request.user.is_superuser or request.user.role == 'ADMINISTRATIVO'))


class ActividadLogViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly para logs
    queryset = ActividadLog.objects.all()
    serializer_class = ActividadLogSerializer
    permission_classes = [IsAdminOrSuperuser] # Solo admins/superusers pueden ver logs

    def get_queryset(self):
        """Filtra logs por empresa del usuario si no es superusuario."""
        user = self.request.user
        if user.is_superuser:
            return ActividadLog.objects.all()
        elif user.empresa:
            return ActividadLog.objects.filter(empresa=user.empresa)
        return ActividadLog.objects.none()