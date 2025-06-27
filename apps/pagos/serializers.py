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

