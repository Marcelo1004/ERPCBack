from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Empresa
from .serializers import EmpresaSerializer
from apps.usuarios.views import IsSuperUser, IsAdminUserOrSuperUser # Importa tus permisos personalizados

class EmpresaPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Permitir listar empresas (solo superusuarios pueden crear en esta vista)
        if view.action == 'list' and request.user.is_superuser:
            return True
        # Permitir creación de empresas (solo superusuarios)
        if view.action == 'create' and request.user.is_superuser:
            return True
        # Para retrieve, update, destroy, el permiso se verifica en has_object_permission
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Superusuario siempre tiene permiso total
        if request.user.is_superuser:
            return True

        # Si el usuario es ADMINISTRATIVO o EMPLEADO
        if request.user.is_authenticated and request.user.empresa == obj:
            # POST no debería llegar aquí si ya se maneja en has_permission
            if request.method in permissions.SAFE_METHODS: # GET (lectura)
                return True
            # PUT/PATCH (actualización)
            if request.method in ['PUT', 'PATCH'] and request.user.role == 'ADMINISTRATIVO':
                return True
            # DELETE (ningún admin de empresa puede eliminar la empresa)
            return False
        return False # Denegar por defecto

class EmpresaListView(generics.ListCreateAPIView):
    """
    Vista para listar todas las empresas (solo SuperUser) y crear una nueva empresa (solo SuperUser).
    """
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsSuperUser] # Solo SuperUser puede listar y crear empresas

    def perform_create(self, serializer):
        serializer.save()

class EmpresaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    lookup_field = 'pk'
    permission_classes = [EmpresaPermission] # Usamos el permiso personalizado

    def get_queryset(self):
        # Si no es superusuario, solo permite ver la empresa a la que pertenece
        if self.request.user.is_superuser:
            return Empresa.objects.all()
        elif self.request.user.is_authenticated and self.request.user.empresa:
            return Empresa.objects.filter(pk=self.request.user.empresa.pk)
        return Empresa.objects.none() # No debe ver ninguna empresa si no está ligado

    def perform_destroy(self, instance):
        instance.delete()

