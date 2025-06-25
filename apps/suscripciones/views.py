from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Suscripcion
from .serializers import SuscripcionSerializer
from apps.usuarios.views import IsAdminUserOrSuperUser, IsSuperUser

class SuscripcionListView(generics.ListCreateAPIView):
    queryset = Suscripcion.objects.all()
    serializer_class = SuscripcionSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [AllowAny] # ¡Cualquier usuario (sin o con cuenta) puede ver los planes!
        else: # Para POST
            permission_classes = [IsSuperUser] # Solo superusuarios pueden crear/modificar planes
        return [permission() for permission in permission_classes]

class SuscripcionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Suscripcion.objects.all()
    serializer_class = SuscripcionSerializer
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [AllowAny] # ¡Cualquier usuario (sin o con cuenta) puede ver los detalles del plan!
        else: # Para PUT, PATCH, DELETE
            permission_classes = [IsSuperUser] 
        return [permission() for permission in permission_classes]
