# apps/pagos/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.db.models import Q  # Importa Q para filtros complejos

from .models import Pago
from .serializers import PagoSerializer


# Asume que ya tienes definidas las siguientes clases de permiso en tu proyecto
# Si no las tienes, asegúrate de importarlas desde tu módulo de permisos
# Por ejemplo: from apps.usuarios.permissions import IsSuperUser, IsAdministrador, IsEmpleado
# O simplemente usa IsAuthenticated para empezar y luego refinar.

class IsSuperUser(BasePermission):
    """Permite el acceso sólo a superusuarios."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class IsAdministrador(BasePermission):
    """Permite el acceso sólo a usuarios con rol 'Administrador'."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and \
            hasattr(request.user, 'role') and \
            (isinstance(request.user.role, str) and request.user.role == 'ADMINISTRATIVO' or \
             (hasattr(request.user.role, 'name') and request.user.role.name == 'Administrador'))


class IsEmpleado(BasePermission):
    """Permite el acceso sólo a usuarios con rol 'Empleado'."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and \
            hasattr(request.user, 'role') and \
            (isinstance(request.user.role, str) and request.user.role == 'EMPLEADO' or \
             (hasattr(request.user.role, 'name') and request.user.role.name == 'Empleado'))


class PagoViewSet(viewsets.ModelViewSet):
    """
    API para la gestión de Pagos.
    Permite a superusuarios ver todos los pagos.
    Permite a administradores y empleados ver pagos de su empresa.
    Permite crear pagos.
    """
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]  # Por defecto, solo autenticados

    def get_queryset(self):
        """
        Filtra los pagos basados en el rol del usuario.
        Superusuarios ven todos los pagos.
        Administradores y Empleados ven pagos de su propia empresa.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser:
            # Superusuarios pueden filtrar por empresa_id en la URL
            empresa_id = self.request.query_params.get('empresa_id')
            if empresa_id:
                queryset = queryset.filter(empresa_id=empresa_id)
            return queryset
        elif user.is_authenticated and user.empresa:
            # Administradores y Empleados ven solo pagos de su empresa
            # Asegúrate de que tu modelo CustomUser tenga un campo 'empresa' o 'empresa_detail'
            # que apunte a la empresa del usuario.
            if hasattr(user, 'role') and \
                    (isinstance(user.role, str) and user.role in ['ADMINISTRATIVO', 'EMPLEADO'] or \
                     (hasattr(user.role, 'name') and user.role.name in ['Administrador', 'Empleado'])):
                return queryset.filter(empresa=user.empresa)
            else:
                # Si el usuario autenticado no tiene un rol permitido para ver pagos
                return Pago.objects.none()  # No mostrar ningún pago
        return Pago.objects.none()  # Si no está autenticado o no tiene empresa, no mostrar nada

    def get_permissions(self):
        """
        Define permisos más detallados por acción.
        - Listar y Recuperar: IsSuperUser O (IsAdministrador Y PropiaEmpresa) O (IsEmpleado Y PropiaEmpresa)
        - Crear: IsAuthenticated (cualquiera puede crear un pago si viene del carrito)
        - Actualizar/Eliminar: Solo SuperUser (para mantener la integridad de los pagos)
        """
        if self.action in ['list', 'retrieve']:
            # Permisos para ver pagos: Superuser, o Admin/Empleado de la misma empresa
            self.permission_classes = [
                IsSuperUser | (IsAdministrador & IsAuthenticated) | (IsEmpleado & IsAuthenticated)]
        elif self.action == 'create':
            # Cualquiera autenticado puede crear un pago (ej. desde el carrito)
            self.permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Actualizar y eliminar son restringidos (idealmente solo por sistema o superuser)
            self.permission_classes = [IsSuperUser]  # Muy restrictivo para mantener integridad de pagos
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo pago.
        Asegura que el `cliente` y `empresa` se asignen automáticamente si no se proveen
        y el usuario autenticado tiene esos datos.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Si el usuario es un cliente y no se proporciona 'cliente', asignarlo
        if request.user.is_authenticated and hasattr(request.user, 'role') and \
                ((isinstance(request.user.role, str) and request.user.role == 'CLIENTE') or \
                 (hasattr(request.user.role, 'name') and request.user.role.name == 'Cliente')) and \
                not serializer.validated_data.get('cliente'):
            serializer.validated_data['cliente'] = request.user

        # Si la empresa no se proporciona, y el usuario autenticado está asociado a una empresa
        if not serializer.validated_data.get('empresa') and request.user.is_authenticated and request.user.empresa:
            serializer.validated_data['empresa'] = request.user.empresa

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # Nota: No permitimos update/destroy de pagos directamente por API para mantener la integridad.
    # Si se necesita un "reembolso" o "anulación", se debería crear una nueva transacción de pago negativa
    # o un cambio de estado específico que no elimine el registro original.
    # Los métodos 'update' y 'destroy' no están sobreescritos aquí, por lo que usarán los permisos de ModelViewSet.
    # Si quieres deshabilitarlos completamente, podrías hacer:
    # def update(self, request, *args, **kwargs):
    #    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # def destroy(self, request, *args, **kwargs):
    #    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


# apps/pagos/serializers.py

from rest_framework import serializers
from .models import Pago
from apps.usuarios.models import CustomUser
from apps.empresas.models import Empresa
from apps.ventas.models import Venta
from decimal import Decimal


class PagoSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar nombres de objetos relacionados
    cliente_nombre = serializers.CharField(source='cliente.first_name', read_only=True, allow_null=True)
    cliente_email = serializers.CharField(source='cliente.email', read_only=True, allow_null=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    # Si la relación es OneToOne, podemos simplemente usar el campo 'venta' directamente
    # y el cliente puede enviar el ID de la venta.
    venta_id = serializers.PrimaryKeyRelatedField(source='venta', read_only=True)  # ID de la venta, read-only

    class Meta:
        model = Pago
        fields = [
            'id', 'venta', 'venta_id', 'cliente', 'cliente_nombre', 'cliente_email',
            'empresa', 'empresa_nombre', 'monto', 'fecha_pago', 'metodo_pago',
            'referencia_transaccion', 'estado_pago', 'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = [
            'fecha_creacion', 'fecha_actualizacion', 'cliente_nombre', 'cliente_email',
            'empresa_nombre', 'venta_id'
        ]
        # Aseguramos que 'venta', 'cliente', 'empresa' puedan ser enviados como IDs
        extra_kwargs = {
            'venta': {'write_only': True, 'required': False, 'allow_null': True},
            'cliente': {'write_only': True},
            'empresa': {'write_only': True},
        }

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto del pago debe ser un número positivo.")
        return value

    def validate(self, data):
        # Validar que las FKs/OneToOneField existan si se proporcionan como IDs
        # Convertir IDs a objetos de modelo
        if 'cliente' in data and isinstance(data['cliente'], int):
            try:
                data['cliente'] = CustomUser.objects.get(id=data['cliente'])
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"cliente": "El cliente con este ID no existe."})
        elif 'cliente' not in data or data['cliente'] is None:
            raise serializers.ValidationError({"cliente": "El cliente es un campo requerido."})

        if 'empresa' in data and isinstance(data['empresa'], int):
            try:
                data['empresa'] = Empresa.objects.get(id=data['empresa'])
            except Empresa.DoesNotExist:
                raise serializers.ValidationError({"empresa": "La empresa con este ID no existe."})
        elif 'empresa' not in data or data['empresa'] is None:
            raise serializers.ValidationError({"empresa": "La empresa es un campo requerido."})

        # Validación para el campo OneToOneField 'venta'
        if 'venta' in data and isinstance(data['venta'], int):
            try:
                venta_obj = Venta.objects.get(id=data['venta'])
                # Opcional: Validar que esta venta no tenga ya un pago asociado
                if hasattr(venta_obj, 'pago') and venta_obj.pago and (
                        self.instance is None or venta_obj.pago.id != self.instance.id):
                    raise serializers.ValidationError({"venta": "Esta venta ya tiene un pago asociado."})
                data['venta'] = venta_obj
            except Venta.DoesNotExist:
                raise serializers.ValidationError({"venta": "La venta con este ID no existe."})
        elif 'venta' in data and data['venta'] is None:
            # Permitir que la venta sea nula si se envía explícitamente como None
            data['venta'] = None
        # Si 'venta' no se envía, se asume null por el 'required=False, allow_null=True' en extra_kwargs

        return data

    # Sobreescribir create y update para manejar las relaciones de forma explícita
    def create(self, validated_data):
        # Las instancias de cliente, empresa, y venta (si existen) ya están en validated_data
        # gracias a los métodos validate anteriores.
        return Pago.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Actualizar campos directos
        instance.monto = validated_data.get('monto', instance.monto)
        instance.fecha_pago = validated_data.get('fecha_pago', instance.fecha_pago)
        instance.metodo_pago = validated_data.get('metodo_pago', instance.metodo_pago)
        instance.referencia_transaccion = validated_data.get('referencia_transaccion', instance.referencia_transaccion)
        instance.estado_pago = validated_data.get('estado_pago', instance.estado_pago)

        # Actualizar relaciones si están presentes en validated_data
        if 'cliente' in validated_data:
            instance.cliente = validated_data['cliente']
        if 'empresa' in validated_data:
            instance.empresa = validated_data['empresa']
        if 'venta' in validated_data:
            instance.venta = validated_data['venta']

        instance.save()
        return instance

