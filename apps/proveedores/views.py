# apps/compras_proveedores/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Proveedor
from .serializers import ProveedorSerializer
from apps.usuarios.views import IsSuperUser, IsAdminUserOrSuperUser  # Asegúrate de que esta importación sea correcta
from django.db import transaction


class ProveedorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Proveedores.
    Permite a superusuarios y personal administrativo gestionar proveedores.
    Los usuarios no superusuarios solo pueden ver y gestionar proveedores de su propia empresa.
    """
    queryset = Proveedor.objects.all().order_by('nombre')
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrSuperUser]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Proveedor.objects.all().order_by('nombre')
        elif user.empresa:
            return Proveedor.objects.filter(empresa=user.empresa).order_by('nombre')
        return Proveedor.objects.none()

    def get_serializer_context(self):
        # Pasa el objeto request al serializador para que pueda acceder a request.user
        return {'request': self.request}

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser and user.empresa:
            serializer.save(empresa=user.empresa)
        else:
            serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_superuser and user.empresa:
            # Asegura que no se intente cambiar la empresa si no es superuser
            if serializer.instance.empresa != user.empresa:
                raise Exception("No tiene permiso para modificar proveedores de otra empresa.")
            serializer.save(empresa=user.empresa)
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = self.request.user
        # Solo permitir eliminar si es superuser o si es administrativo de la misma empresa
        if not user.is_superuser and user.empresa and instance.empresa != user.empresa:
            return Response({"detail": "No tiene permiso para eliminar proveedores de otra empresa."},
                            status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

# No añadimos los ViewSets de Compra/DetalleCompra aún.