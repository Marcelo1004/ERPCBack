from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import Movimiento, DetalleMovimiento
from .serializers import MovimientoSerializer, DetalleMovimientoSerializer
from apps.productos.models import Producto
from erp.permissions import IsAdminOrSuperUser, IsEmployeeOrHigher


class MovimientoFilter(DjangoFilterBackend):
    class Meta:
        model = Movimiento
        fields = {
            'empresa': ['exact'],
            'proveedor': ['exact'],
            'almacen_destino': ['exact'],
            'estado': ['exact'],
        }

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)

        search_query = request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(observaciones__icontains=search_query) |
                Q(detalles__producto__nombre__icontains=search_query) |
                Q(detalles__producto__codigo__icontains=search_query)
            ).distinct()

        return queryset


class MovimientoViewSet(viewsets.ModelViewSet):
    queryset = Movimiento.objects.all()
    serializer_class = MovimientoSerializer

    filter_backends = [MovimientoFilter, filters.OrderingFilter]
    ordering_fields = [
        'id', 'fecha_llegada', 'costo_transporte', 'monto_total_operacion',
        'created_at',
        'updated_at',
        'estado',
        'empresa__nombre', 'proveedor__nombre', 'almacen_destino__nombre'
    ]
    ordering = ['-fecha_llegada', '-created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'aceptar', 'rechazar']:
            self.permission_classes = [IsAdminOrSuperUser]
        else:  # 'list', 'retrieve'
            self.permission_classes = [IsEmployeeOrHigher]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = Movimiento.objects.all()

        if user.is_authenticated:
            if user.is_superuser:
                pass
            elif hasattr(user, 'empresa_detail') and user.empresa_detail:
                queryset = queryset.filter(empresa=user.empresa_detail)
            else:
                return Movimiento.objects.none()
        else:
            return Movimiento.objects.none()

        queryset = queryset.select_related(
            'empresa', 'proveedor', 'almacen_destino'
        ).prefetch_related(
            'detalles__producto'
        )

        return queryset

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_destroy(self, instance):
        with transaction.atomic():
            for detalle in instance.detalles.all():
                producto = detalle.producto
                cantidad = detalle.cantidad_suministrada

                # Solo revertir stock si el movimiento estaba ACEPTADO
                if instance.estado == 'Aceptado':
                    # Determinar si el movimiento original fue una entrada o salida
                    # para revertir correctamente el stock.
                    if instance.proveedor:  # Si fue una entrada, ahora hay que restar stock
                        if producto.stock < cantidad:
                            raise ValidationError(
                                f"No se puede eliminar el movimiento (entrada) porque el stock del producto '{producto.nombre}' "
                                f"sería negativo al revertir. Stock actual: {producto.stock}, cantidad a revertir: {cantidad}."
                            )
                        producto.stock -= cantidad
                    else:  # Si fue una salida, ahora hay que sumar stock
                        producto.stock += cantidad
                    producto.save(update_fields=['stock'])
            instance.delete()

    # === ACCIONES PARA CAMBIAR EL ESTADO ===
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperUser])
    def aceptar(self, request, pk=None):
        movimiento = self.get_object()
        if movimiento.estado == 'Pendiente':
            movimiento.estado = 'Aceptado'

            with transaction.atomic():
                # === LÓGICA DE AJUSTE DE STOCK CONSOLIDADA AQUÍ ===
                # Se infiere el tipo de movimiento basado en la presencia de 'proveedor'
                if movimiento.proveedor:  # Si hay proveedor, es una ENTRADA
                    for detalle in movimiento.detalles.all():
                        producto = detalle.producto
                        producto.stock += detalle.cantidad_suministrada  # Sumar stock
                        producto.save(update_fields=['stock'])
                else:  # Si NO hay proveedor, es una SALIDA
                    for detalle in movimiento.detalles.all():
                        producto = detalle.producto
                        if producto.stock < detalle.cantidad_suministrada:
                            raise ValidationError(
                                f"Stock insuficiente para el producto '{producto.nombre}' para completar la salida. "
                                f"Stock actual: {producto.stock}, cantidad solicitada: {detalle.cantidad_suministrada}."
                            )
                        producto.stock -= detalle.cantidad_suministrada  # Restar stock
                        producto.save(update_fields=['stock'])

                movimiento.save()  # Guarda el cambio de estado (y triggers updated_at)

            return Response({'status': 'Movimiento aceptado', 'movimiento_id': movimiento.id},
                            status=status.HTTP_200_OK)
        return Response({'error': 'El movimiento no está Pendiente o ya fue procesado.'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperUser])
    def rechazar(self, request, pk=None):
        movimiento = self.get_object()
        if movimiento.estado == 'Pendiente':
            movimiento.estado = 'Rechazado'
            # NO se ajusta stock al rechazar
            movimiento.save()
            return Response({'status': 'Movimiento rechazado', 'movimiento_id': movimiento.id},
                            status=status.HTTP_200_OK)
        return Response({'error': 'El movimiento no está Pendiente o ya fue procesado.'},
                        status=status.HTTP_400_BAD_REQUEST)