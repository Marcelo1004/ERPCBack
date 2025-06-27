# apps/usuarios/views.py

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import filters
import django_filters.rest_framework
from rest_framework import viewsets

# Importa tus serializers
from .serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    AdminUserUpdateSerializer,
    CustomTokenObtainPairSerializer
)

# Importa tu modelo CustomUser (importación relativa ya que está en la misma app)
from .models import CustomUser

# Importa tu permiso centralizado
from erp.permissions import IsAdminOrSuperUser # <-- ¡Esta línea es CRUCIAL y apunta a tu archivo central!

from rest_framework_simplejwt.views import TokenObtainPairView


# --- Vistas ---

# 1. Autenticación Personalizada con JWT
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    # TokenObtainPairView de Simple JWT ya maneja el método POST por defecto.
    # Si sigues obteniendo un 405 aquí, el problema no está en esta vista,
    # sino en una configuración más profunda de Django REST Framework o en el cliente.


# 2. Registro de Nuevo Usuario
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegisterSerializer


# 3. Perfil de Usuario (para que el propio usuario vea/edite su información)
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=False, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(UserProfileSerializer(user, context={'request': request}).data)

    def patch(self, request):
        user = request.user
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(UserProfileSerializer(user, context={'request': request}).data)


# 4. Gestión de Usuarios por Administrador (ModelViewSet)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de usuarios por parte de SuperUsuarios o Administradores/Empleados.
    Proporciona operaciones de listado, creación, detalle, actualización y eliminación.
    """
    queryset = CustomUser.objects.all()
    permission_classes = [IsAdminOrSuperUser] # <-- Usando el permiso centralizado

    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'ci', 'telefono']
    filterset_fields = {
        'role__name': ['exact'],
        'empresa': ['exact'],
    }

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CustomUser.objects.none()

        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset.order_by('username')
        elif user.is_authenticated and hasattr(user, 'role') and user.role and user.role.name in ['Administrador', 'Empleado']:
            if hasattr(user, 'empresa') and user.empresa:
                return queryset.filter(empresa=user.empresa).order_by('username')
            return CustomUser.objects.none()
        else:
            return CustomUser.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegisterSerializer
        elif self.action in ['update', 'partial_update']:
            return AdminUserUpdateSerializer
        return UserProfileSerializer

    def perform_create(self, serializer):
        request_user = self.request.user

        if request_user.is_superuser:
            serializer.save()
        elif request_user.is_authenticated and hasattr(request_user, 'role') and request_user.role and request_user.role.name in ['Administrador', 'Empleado']:
            target_role = serializer.validated_data.get('role')

            if target_role and (target_role.name == 'Super Usuario' or target_role.name in ['Administrador', 'Empleado']):
                raise PermissionDenied(
                    "Solo un Super Usuario puede crear otros usuarios administrativos o superusuarios."
                )

            if hasattr(request_user, 'empresa') and request_user.empresa:
                if 'empresa' in serializer.validated_data and serializer.validated_data['empresa'] != request_user.empresa:
                    raise PermissionDenied({"empresa": "No puedes crear usuarios en otra empresa."})
                serializer.save(empresa=request_user.empresa)
            else:
                raise PermissionDenied("Tu cuenta no está asociada a una empresa para crear usuarios.")
        else:
            raise PermissionDenied("No tienes permiso para crear usuarios.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_superuser:
            if request.user.id != instance.id:
                if not request.user.is_superuser:
                    raise PermissionDenied("No se puede eliminar a un Super Usuario sin ser Super Usuario.")
            else:
                raise PermissionDenied("Un Super Usuario no puede eliminar su propia cuenta a través de esta API.")

        if request.user == instance:
            raise PermissionDenied("No puedes eliminar tu propia cuenta a través de esta API.")

        if (request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role and
                request.user.role.name in ['Administrador', 'Empleado'] and
                hasattr(request.user, 'empresa') and request.user.empresa):
            if instance.empresa != request.user.empresa:
                raise PermissionDenied("No tienes permiso para eliminar usuarios de otra empresa.")
            if instance.is_superuser:
                 raise PermissionDenied("No tienes permiso para eliminar a un Super Usuario.")
            if instance.role and instance.role.name in ['Administrador', 'Empleado']:
                 raise PermissionDenied("Un ADMINISTRATIVO/EMPLEADO no puede eliminar a otros ADMINISTRATIVOS/EMPLEADOS.")

        username = instance.username
        self.perform_destroy(instance)
        return Response(
            {"detail": f"Usuario {username} eliminado correctamente."},
            status=status.HTTP_204_NO_CONTENT
        )