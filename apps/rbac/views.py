from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser # Permiso integrado de DRF para SuperUser
from rest_framework.response import Response # Importar Response
from .models import Permission, Role
from .serializers import PermissionSerializer, RoleSerializer

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all().order_by('id')
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser] # Restringe el acceso solo a superusuarios de Django

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by('name').prefetch_related('permissions') # Optimizar query
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser] # Restringe el acceso solo a superusuarios de Django

