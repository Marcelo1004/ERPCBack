# apps/compras_proveedores/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import transaction

from .models import Proveedor
from .serializers import ProveedorSerializer

# Asegúrate de que estas importaciones y definiciones de permisos sean correctas
# y que IsAdminOrSuperUser maneje request.user.role.name consistentemente.
from erp.permissions import IsSuperUser, IsAdminOrSuperUser # <- Revisa la definición de estas clases


class ProveedorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Proveedores.
    Permite a superusuarios y personal administrativo gestionar proveedores.
    Los usuarios no superusuarios solo pueden ver y gestionar proveedores de su propia empresa.
    """
    queryset = Proveedor.objects.all().order_by('nombre')
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser] # Aplica tus permisos aquí

    def get_queryset(self):
        # === INICIO DE LA CORRECCIÓN CRÍTICA PARA SWAGGER/AnonymousUser ===
        if getattr(self, 'swagger_fake_view', False):
            return Proveedor.objects.none()
        # === FIN DE LA CORRECCIÓN ===

        user = self.request.user

        if user.is_superuser:
            return Proveedor.objects.all().order_by('nombre')
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            return Proveedor.objects.filter(empresa=user.empresa).order_by('nombre')

        return Proveedor.objects.none()

    def get_serializer_context(self):
        # Pasa el objeto request al serializador para que pueda acceder a request.user
        return {'request': self.request}

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser:
            if not (user.is_authenticated and hasattr(user, 'empresa') and user.empresa):
                raise PermissionDenied("Debe estar autenticado y asociado a una empresa para crear proveedores.")
            serializer.save(empresa=user.empresa)
        else:
            serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance # Obtener la instancia actual antes de guardar
        user = self.request.user

        if not user.is_superuser:
            if not (user.is_authenticated and hasattr(user, 'empresa') and user.empresa):
                raise PermissionDenied("Debe estar autenticado y asociado a una empresa para modificar proveedores.")

            # Asegura que no se intente cambiar la empresa si no es superusuario
            # y que el proveedor pertenezca a la misma empresa del usuario.
            if instance.empresa != user.empresa:
                raise PermissionDenied("No tiene permiso para modificar proveedores de otra empresa.")

            # Si el proveedor pertenece a la misma empresa, guarda.
            # Esto también asegura que 'empresa' no se cambie si el serializer intentó hacerlo sin permiso.
            serializer.save(empresa=user.empresa)
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if not user.is_superuser:
            if not (user.is_authenticated and hasattr(user, 'empresa') and user.empresa):
                raise PermissionDenied("Debe estar autenticado y asociado a una empresa para eliminar proveedores.")

            if instance.empresa != user.empresa:
                raise PermissionDenied("No tiene permiso para eliminar proveedores de otra empresa.")

            # Revisa que el rol sea 'Administrador' (o el que uses para administrar proveedores)
            if not (hasattr(user, 'role') and user.role and user.role.name == 'Administrador'): # Ajusta 'Administrador' si tu rol tiene otro nombre
                raise PermissionDenied("Su rol no le permite eliminar proveedores.")

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)