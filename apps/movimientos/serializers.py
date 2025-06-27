# your_app_name/serializers.py

from rest_framework import serializers
from django.db import transaction
from .models import Movimiento, DetalleMovimiento
from apps.productos.models import Producto


# Asegúrate de importar Proveedor, Almacen, Empresa si las usas en modelos relacionados.
# from apps.proveedores.models import Proveedor
# from apps.almacenes.models import Almacen
# from apps.empresas.models import Empresa


class DetalleMovimientoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)

    class Meta:
        model = DetalleMovimiento
        fields = ['id', 'producto', 'producto_nombre', 'producto_codigo',
                  'cantidad_suministrada', 'colores', 'valor_unitario', 'valor_total_producto']
        read_only_fields = ['valor_total_producto', 'producto_nombre', 'producto_codigo']

    def validate(self, data):
        cantidad = data.get('cantidad_suministrada')
        valor = data.get('valor_unitario')

        if cantidad is not None and cantidad <= 0:
            raise serializers.ValidationError("La cantidad suministrada debe ser mayor a 0.")
        if valor is not None and valor <= 0:
            raise serializers.ValidationError("El valor unitario debe ser mayor a 0.")
        return data


class MovimientoSerializer(serializers.ModelSerializer):
    detalles = DetalleMovimientoSerializer(many=True, required=False)

    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True, allow_null=True)
    almacen_destino_nombre = serializers.CharField(source='almacen_destino.nombre', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Movimiento
        fields = [
            'id', 'empresa', 'empresa_nombre', 'proveedor', 'proveedor_nombre',
            'almacen_destino', 'almacen_destino_nombre', 'fecha_llegada',
            'observaciones', 'costo_transporte', 'monto_total_operacion',
            'detalles', 'estado'
        ]
        read_only_fields = ['monto_total_operacion', 'estado']  # 'estado' sigue siendo read_only para el form

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])

        request = self.context.get('request')
        if request and request.user and not request.user.is_superuser:
            if not validated_data.get('empresa') and request.user.empresa_detail:
                validated_data['empresa'] = request.user.empresa_detail
            elif validated_data.get('empresa') and validated_data.get('empresa') != request.user.empresa_detail:
                raise serializers.ValidationError(
                    {"empresa": "No tienes permiso para crear movimientos para esta empresa."})
            elif not validated_data.get('empresa') and not request.user.empresa_detail:
                raise serializers.ValidationError({"empresa": "La empresa es requerida para tu usuario."})

        with transaction.atomic():
            # El campo 'estado' se establece automáticamente a 'Pendiente' por el modelo
            movimiento = Movimiento.objects.create(**validated_data)
            total_monto_productos = 0

            for detalle_data in detalles_data:
                # NO MODIFICAR STOCK AQUÍ
                producto_id = detalle_data.pop('producto').id
                producto = Producto.objects.get(id=producto_id)

                DetalleMovimiento.objects.create(movimiento=movimiento, producto=producto, **detalle_data)
                total_monto_productos += detalle_data['cantidad_suministrada'] * detalle_data['valor_unitario']

            movimiento.monto_total_operacion = total_monto_productos + movimiento.costo_transporte
            movimiento.save(update_fields=['monto_total_operacion'])

        return movimiento

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', None)

        # Actualiza campos del Movimiento principal (excepto 'estado')
        for attr, value in validated_data.items():
            if attr == 'estado':
                continue
            setattr(instance, attr, value)
        instance.save()

        if detalles_data is not None:
            with transaction.atomic():
                current_detalle_ids = set()
                new_total_monto_productos = 0

                original_detalles_map = {d.id: d for d in instance.detalles.all()}

                for detalle_data in detalles_data:
                    detalle_id = detalle_data.get('id')
                    producto_obj_or_id = detalle_data.pop('producto')

                    if isinstance(producto_obj_or_id, Producto):
                        producto_obj = producto_obj_or_id
                    else:
                        producto_obj = Producto.objects.get(id=producto_obj_or_id)

                    cantidad_nueva = detalle_data['cantidad_suministrada']
                    valor_unitario_nuevo = detalle_data['valor_unitario']

                    if detalle_id and detalle_id in original_detalles_map:
                        # ES UN DETALLE EXISTENTE (ACTUALIZACIÓN)
                        current_detalle_instance = original_detalles_map[detalle_id]
                        # NO MODIFICAR STOCK AQUÍ

                        for d_attr, d_value in detalle_data.items():
                            setattr(current_detalle_instance, d_attr, d_value)
                        current_detalle_instance.producto = producto_obj
                        current_detalle_instance.save()

                        current_detalle_ids.add(current_detalle_instance.id)

                    else:
                        # ES UN NUEVO DETALLE
                        # NO MODIFICAR STOCK AQUÍ

                        new_detalle_instance = DetalleMovimiento.objects.create(movimiento=instance,
                                                                                producto=producto_obj, **detalle_data)
                        current_detalle_ids.add(new_detalle_instance.id)

                    new_total_monto_productos += cantidad_nueva * valor_unitario_nuevo

                # Eliminar detalles que ya no están y REVERTIR stock (si el movimiento ya estaba ACEPTADO)
                # Esta lógica de reversión al eliminar detalles debe estar muy alineada con
                # cuándo se ajusta el stock. Si el movimiento se acepta DESPUÉS de la edición,
                # esta parte de reversión no debería ocurrir aquí.
                # Se recomienda que la reversión de stock solo ocurra en perform_destroy
                # cuando se elimina el movimiento completo.
                for detail_id, detail_instance in original_detalles_map.items():
                    if detail_id not in current_detalle_ids:
                        # Si un detalle se elimina durante una edición, y el movimiento ya estaba 'Aceptado',
                        # entonces SÍ debemos revertir el stock de ese detalle.
                        if instance.estado == 'Aceptado':
                            producto_a_disminuir = detail_instance.producto
                            cantidad_a_disminuir = detail_instance.cantidad_suministrada
                            producto_a_disminuir.stock -= cantidad_a_disminuir
                            producto_a_disminuir.save(update_fields=['stock'])

                        detail_instance.delete()

                instance.monto_total_operacion = new_total_monto_productos + instance.costo_transporte
                instance.save(update_fields=['monto_total_operacion'])

        return instance