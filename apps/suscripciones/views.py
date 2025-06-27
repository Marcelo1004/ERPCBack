from rest_framework import viewsets, permissions, status
from rest_framework.response import Response # Asegúrate de que Response esté importado

from .models import Suscripcion
from .serializers import SuscripcionSerializer
from rest_framework.permissions import IsAdminUser

class SuscripcionViewSet(viewsets.ModelViewSet):
    queryset = Suscripcion.objects.all().order_by('nombre')
    serializer_class = SuscripcionSerializer
    lookup_field = 'pk' # Asegura que el detalle se busque por 'pk' (id)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        # Para acciones de escritura (create, update, partial_update, destroy), solo SuperUsuarios.
        return [IsAdminUser()]

    def get_queryset(self):
        """
        Optimización para Swagger/AnonymousUser y ordenamiento.
        """
        # Esta línea es crucial para evitar cualquier AttributeError si el inspector de Swagger
        # intentara acceder a atributos de request.user que no existen para AnonymousUser.
        if getattr(self, 'swagger_fake_view', False):
            # Para la generación del esquema, devuelve un QuerySet completo.
            return Suscripcion.objects.all().order_by('nombre')

        # Para solicitudes normales, devuelve el queryset base ya ordenado.
        return super().get_queryset()