from rest_framework import permissions


class IsAdminOrSuperUser(permissions.BasePermission):
    """
    Permite el acceso a superusuarios o usuarios con el rol 'Administrador'.
    Asume que request.user.role es un objeto con un atributo 'name' (request.user.role.name).
    """
    def has_permission(self, request, view):
        if not request.user or request.user.is_anonymous: # is_anonymous para AnonUser
            return False

        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'role') and request.user.role is not None:
            # ¡CRÍTICO: Usar .name para comparar el nombre del rol!
            return request.user.role.name == 'Administrador' # <- Ajusta 'Administrador' si el nombre es diferente

        return False # Denegar si no es superusuario y no tiene un rol válido

# Puedes añadir IsEmployeeOrHigher aquí también si lo usas en otras apps
class IsEmployeeOrHigher(permissions.BasePermission):
    """
    Permite el acceso a superusuarios, administradores o empleados.
    Asume que request.user.role es un objeto con un atributo 'name'.
    """
    def has_permission(self, request, view):
        if not request.user or request.user.is_anonymous:
            return False

        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'role') and request.user.role is not None:
            # ¡CRÍTICO: Usar .name para comparar el nombre del rol!
            return request.user.role.name in ['Administrador', 'Empleado'] # <- Ajusta nombres si son diferentes

        return False

class IsSuperUser(permissions.BasePermission):
        """
        Permiso personalizado para permitir el acceso solo a superusuarios.
        """

        def has_permission(self, request, view):
            # Permite acceso si el usuario está autenticado y es un superusuario
            return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

        def has_object_permission(self, request, view, obj):
            # Para permisos a nivel de objeto, también permite solo a superusuarios
            return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


