# apps/ventas/serializers.py

from rest_framework import serializers
from .models import Venta, DetalleVenta
from apps.productos.models import Producto  # Necesario para verificar el stock


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario']
        # 'venta' no está en fields porque será manejado por el serializer padre (VentaSerializer)

    def validate(self, data):
        # Valida que el producto tenga suficiente stock al crear/actualizar un detalle
        producto = data.get('producto')
        cantidad = data.get('cantidad')

        if producto and cantidad:
            if producto.stock < cantidad:
                raise serializers.ValidationError(
                    f"Stock insuficiente para el producto '{producto.nombre}'. "
                    f"Stock actual: {producto.stock}, solicitado: {cantidad}."
                )
        return data


class VentaSerializer(serializers.ModelSerializer):
    # Detalles ahora es writable para la creación anidada
    detalles = DetalleVentaSerializer(many=True,
                                      required=False)  # `required=False` permite crear ventas sin detalles inicialmente

    usuario_nombre = serializers.CharField(source='usuario.first_name', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Venta
        fields = ['id', 'empresa', 'empresa_nombre', 'usuario', 'usuario_nombre', 'fecha', 'monto_total', 'estado',
                  'detalles']
        read_only_fields = ['monto_total']  # El monto total se calculará, no se recibe directamente en POST/PUT/PATCH

    def create(self, validated_data):
        # Extrae los detalles de venta de los datos validados
        detalles_data = validated_data.pop('detalles', [])

        # Asigna la empresa y el usuario al crear la venta, si no vienen explícitamente
        # Esto es especialmente útil si el frontend no los envía para usuarios no superuser
        request = self.context.get('request')
        if request and request.user and not request.user.is_superuser:
            if not validated_data.get('empresa') and request.user.empresa:
                validated_data['empresa'] = request.user.empresa
            if not validated_data.get('usuario'):  # Si no se envía el usuario cliente en la request
                pass  # Aquí podrías establecer un usuario por defecto o forzar a que venga en la request
                # O, si 'usuario' se refiere al que realiza la venta, lo puedes asignar aquí
                # validated_data['usuario'] = request.user

        # Crea la instancia de la Venta
        venta = Venta.objects.create(**validated_data)

        # Crea cada detalle de venta y asócialo a la venta recién creada
        for detalle_data in detalles_data:
            # Pasa la instancia de la Venta al detalle, y no se requiere el 'venta' en validated_data del detalle
            DetalleVenta.objects.create(venta=venta, **detalle_data)

        # Una vez que los detalles se han creado, recalcula el monto_total de la venta
        venta.monto_total = sum(d.cantidad * d.precio_unitario for d in venta.detalles.all())
        venta.save(update_fields=['monto_total'])  # Guarda solo el monto_total actualizado

        return venta

    def update(self, instance, validated_data):
        # Manejo de la actualización de detalles anidados.
        # Esto es más complejo: requiere identificar qué detalles se borraron, cuáles se modificaron y cuáles se añadieron.
        # Para simplificar por ahora, si hay detalles en la request, los eliminamos y volvemos a crear.
        # En una aplicación real, se preferiría una lógica de diff más sofisticada.

        detalles_data = validated_data.pop('detalles', [])

        # Actualiza los campos de la Venta principal
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Elimina los detalles existentes para recrearlos o actualizarlos
        # CUIDADO: Esto causará que la lógica de .delete() del modelo DetalleVenta
        # se ejecute y potencialmente devuelva stock. Si no quieres eso,
        # necesitarías una lógica más fina para comparar detalles.
        instance.detalles.all().delete()

        # Crea o actualiza los nuevos detalles
        for detalle_data in detalles_data:
            DetalleVenta.objects.create(venta=instance, **detalle_data)

        # Recalcula el monto_total después de actualizar los detalles
        instance.monto_total = sum(d.cantidad * d.precio_unitario for d in instance.detalles.all())
        instance.save(update_fields=['monto_total'])

        return instance