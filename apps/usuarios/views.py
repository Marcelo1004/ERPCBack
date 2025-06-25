from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

# Importa tus serializers y modelos
from .serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    AdminUserUpdateSerializer
)
from .models import User
from apps.empresas.models import Empresa  # Asegúrate de que Empresa esté importada

# Importa las vistas de Simple JWT y su serializador base para extender
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# --- Permisos Personalizados (Actualizados para SaaS Multi-empresa) ---

class IsSuperUser(permissions.BasePermission):
    """
    Permite el acceso solo a superusuarios (del sistema SaaS, no ligados a una empresa cliente).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsAdminUserOrSuperUser(permissions.BasePermission):
    """
    Permite el acceso a superusuarios (del sistema) o a usuarios con rol 'ADMINISTRATIVO'
    (de cualquier empresa). Este permiso es más general.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or request.user.role == 'ADMINISTRATIVO'))


class IsAdminOfOwnCompany(permissions.BasePermission):
    """
    Permite el acceso solo a usuarios con rol 'ADMINISTRATIVO' que estén ligados a una empresa.
    Este permiso es para acciones dentro de su propia empresa.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == 'ADMINISTRATIVO' and request.user.empresa is not None)


class CanManageCompanyUsers(permissions.BasePermission):
    """
    Permiso para listar/crear/gestionar usuarios.
    - SuperUsuario: Puede gestionar todos los usuarios.
    - ADMINISTRATIVO: Solo puede gestionar usuarios de SU PROPIA empresa.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            # Superusuario puede hacer cualquier cosa
            if request.user.is_superuser:
                return True
            # Administrador de empresa
            if request.user.role == 'ADMINISTRATIVO' and request.user.empresa:
                # Si es un GET (lista) o POST (crear usuario de su empresa)
                if request.method in permissions.SAFE_METHODS or request.method == 'POST':
                    return True
                # Para PUT/PATCH/DELETE, se necesita verificar el objeto en has_object_permission
                return True  # Permite pasar a has_object_permission para más granularidad
        return False

    def has_object_permission(self, request, view, obj):
        # Superusuario puede modificar/eliminar cualquier usuario
        if request.user.is_superuser:
            return True

        # Administrador de empresa solo puede gestionar usuarios de su propia empresa
        if request.user.role == 'ADMINISTRATIVO' and request.user.empresa:
            # Asegura que el usuario a gestionar pertenezca a la misma empresa del admin
            if obj.empresa == request.user.empresa:
                # Un admin no puede modificar a otro SuperUsuario del sistema SaaS
                if obj.is_superuser:
                    return False
                # Un admin no puede modificar a un usuario de otra empresa (ya cubierto por obj.empresa check)
                # Un admin puede ver, actualizar, eliminar usuarios de su propia empresa
                return True
        return False  # Denegar por defecto


# --- Vistas ---

# 1. Autenticación Personalizada con JWT (Revertido a solo login por username)
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Simple JWT usa 'username' por defecto, no necesitamos especificarlo si queremos username
    # username_field = 'username' # Se puede dejar comentado o eliminar, ya es el default

    def validate(self, attrs):
        # El validate del padre (TokenObtainPairSerializer) autenticará directamente con el campo 'username'
        data = super().validate(attrs)
        user = self.user  # self.user es establecido por super().validate(attrs) después de una autenticación exitosa

        # Incluye todos los datos del perfil del usuario autenticado en la respuesta del token
        serializer = UserProfileSerializer(user)
        data['user'] = serializer.data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista para obtener tokens JWT. Incluye los datos del usuario en la respuesta.
    """
    serializer_class = CustomTokenObtainPairSerializer


# 2. Registro de Nuevo Usuario
class RegisterView(generics.CreateAPIView):
    """
    Permite el registro de nuevos usuarios.
    Maneja el flujo de registro inicial de una empresa o la unión a una existente.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]  # Cualquiera puede registrarse
    serializer_class = UserRegisterSerializer


# 3. Perfil de Usuario (para que el propio usuario vea/edite su información)
class UserProfileView(APIView):
    """
    Permite a un usuario autenticado ver (GET) y actualizar (PUT/PATCH) su propio perfil.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    def put(self, request):
        # 'partial=True' permite actualizar solo algunos campos
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 4. Gestión de Usuarios por Administrador (Listar)
class UserListView(generics.ListAPIView):
    """
    Permite listar usuarios.
    - SuperUsuario: Lista todos los usuarios del sistema.
    - ADMINISTRATIVO: Lista solo los usuarios de su propia empresa.
    Permite filtrar por 'rol' en query params.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [CanManageCompanyUsers]  # Usa el permiso CanManageCompanyUsers

    def get_queryset(self):
        # Superusuario ve todos los usuarios
        if self.request.user.is_superuser:
            queryset = User.objects.all()
        # Administrador de empresa solo ve usuarios de su propia empresa
        elif self.request.user.role == 'ADMINISTRATIVO' and self.request.user.empresa:
            queryset = User.objects.filter(empresa=self.request.user.empresa)
        else:
            return User.objects.none()  # Otros roles no deben listar usuarios así

        rol = self.request.query_params.get('rol')
        if rol:
            queryset = queryset.filter(role=rol)
        return queryset


# 5. Gestión de Usuarios por Administrador (Crear, Detalle, Actualizar, Eliminar)
class AdminUserCreateView(generics.CreateAPIView):
    """
    Permite a SuperUsuarios y ADMINISTRATIVOS crear nuevos usuarios.
    - SuperUsuario: Puede crear cualquier usuario, asignando cualquier empresa y rol (excepto otros superusuarios).
    - ADMINISTRATIVO: Solo puede crear usuarios para SU PROPIA empresa y asignar roles 'CLIENTE' o 'EMPLEADO'.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer  # Reutilizamos el serializer de registro
    permission_classes = [CanManageCompanyUsers]

    def perform_create(self, serializer):
        user = self.request.user
        # Si es un ADMINISTRATIVO de empresa, se asegura que el usuario se cree en su empresa
        if user.role == 'ADMINISTRATIVO' and user.empresa:
            # Asegura que no intenten crear SUPERUSERs ni ADMINISTRATIVOs de otras empresas
            if serializer.validated_data.get('role') not in ['CLIENTE', 'EMPLEADO']:
                raise permissions.ValidationError(
                    {"role": "Un administrador de empresa solo puede crear usuarios con rol 'CLIENTE' o 'EMPLEADO'."})

            if 'empresa' in serializer.validated_data and serializer.validated_data['empresa'] != user.empresa:
                raise permissions.ValidationError({"empresa": "No puedes crear usuarios en otra empresa."})

            serializer.save(empresa=user.empresa)  # Asigna automáticamente la empresa del admin
        elif user.is_superuser:
            # Superusuario puede crear usuarios en cualquier empresa, o sin empresa (para otros superusuarios)
            # Podríamos añadir validación aquí para que no cree otros superusuarios por este endpoint
            if serializer.validated_data.get('role') == 'SUPERUSER':
                raise permissions.ValidationError(
                    {"role": "No se permite crear SuperUsuarios a través de este endpoint."})
            serializer.save()
        else:
            # Esto no debería ocurrir si CanManageCompanyUsers está bien
            raise permissions.PermissionDenied("No tienes permiso para crear usuarios.")


class AdminUserDetailUpdateDeleteView(APIView):
    """
    Permite obtener detalles (GET), actualizar (PUT/PATCH) o eliminar (DELETE) un usuario específico.
    - SuperUsuario: En cualquier usuario (excepto él mismo).
    - ADMINISTRATIVO: Solo en usuarios de SU PROPIA empresa (excepto él mismo o otros SuperUsuarios).
    """
    permission_classes = [CanManageCompanyUsers]  # Usa el permiso CanManageCompanyUsers

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        self.check_object_permissions(request, user)  # Verifica el permiso a nivel de objeto
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    def put(self, request, user_id):
        user_to_update = get_object_or_404(User, id=user_id)
        self.check_object_permissions(request, user_to_update)  # Verifica el permiso a nivel de objeto

        # No permitir al admin de empresa cambiar el campo 'empresa' o 'is_superuser'/'is_staff'
        if not request.user.is_superuser:
            if 'empresa' in request.data and request.data['empresa'] != user_to_update.empresa.id:
                raise permissions.ValidationError({"empresa": "No puedes cambiar la empresa de un usuario."})
            if 'is_superuser' in request.data or 'is_staff' in request.data:
                raise permissions.ValidationError({"flags": "Solo un Super_Usuario puede modificar flags de sistema."})
            if 'role' in request.data and request.data[
                'role'] == 'ADMINISTRATIVO' and user_to_update.role != 'ADMINISTRATIVO':
                # Esto evita que un admin de empresa cree otro admin de empresa
                raise permissions.ValidationError(
                    {"role": "Un administrador de empresa no puede asignar el rol 'ADMINISTRATIVO'."})
            if 'role' in request.data and request.data['role'] == 'SUPERUSER':
                raise permissions.ValidationError(
                    {"role": "Un administrador de empresa no puede asignar el rol 'SUPERUSER'."})

        serializer = AdminUserUpdateSerializer(user_to_update, data=request.data, partial=True)
        if serializer.is_valid():
            # Asegurarse de que el admin de empresa no cambie la empresa del usuario
            if not request.user.is_superuser and 'empresa' in serializer.validated_data:
                del serializer.validated_data['empresa']  # Ignorar el cambio de empresa si no es superuser

            serializer.save()
            return Response({
                "detail": f"Usuario {user_to_update.username} actualizado correctamente.",
                "user": UserProfileSerializer(user_to_update).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        user_to_delete = get_object_or_404(User, id=user_id)
        self.check_object_permissions(request, user_to_delete)  # Verifica el permiso a nivel de objeto

        # Evitar que un superusuario sea eliminado por cualquier otro usuario
        if user_to_delete.is_superuser:
            return Response(
                {"detail": "No se puede eliminar a un Super_Usuario."},
                status=status.HTTP_403_FORBIDDEN
            )
        # Evitar que un admin o empleado se elimine a sí mismo
        if request.user == user_to_delete:
            return Response(
                {"detail": "No puedes eliminar tu propia cuenta a través de esta API."},
                status=status.HTTP_403_FORBIDDEN
            )

        username = user_to_delete.username
        user_to_delete.delete()
        return Response(
            {"detail": f"Usuario {username} eliminado correctamente."},
            status=status.HTTP_204_NO_CONTENT
        )
