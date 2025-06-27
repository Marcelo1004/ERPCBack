# apps/ventas/serializers.py

from rest_framework import serializers
from django.db import transaction
from apps.productos.models import Producto
from apps.usuarios.models import CustomUser
from apps.empresas.models import Empresa
from .models import Venta, DetalleVenta
from decimal import Decimal


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'descuento_aplicado']
        read_only_fields = ['producto_nombre']

    def validate(self, data):
        cantidad = data.get('cantidad')
        precio_unitario = data.get('precio_unitario')
        descuento_aplicado_raw = data.get('descuento_aplicado')

        # === Validaciones numéricas ===
        if not isinstance(cantidad, (int, float)) or cantidad <= 0:
            raise serializers.ValidationError({"cantidad": "La cantidad debe ser un número positivo."})

        try:
            precio_unitario_decimal = Decimal(str(precio_unitario))
            if precio_unitario_decimal <= 0:
                raise serializers.ValidationError(
                    {"precio_unitario": "El precio unitario debe ser un número positivo."})
            data['precio_unitario'] = precio_unitario_decimal
        except Exception:
            raise serializers.ValidationError({"precio_unitario": "El precio unitario no es un número válido."})

        descuento_aplicado_value = None
        if descuento_aplicado_raw is None or str(descuento_aplicado_raw).strip() == '':
            descuento_aplicado_value = Decimal('0.0000')
        else:
            try:
                descuento_aplicado_value = Decimal(str(descuento_aplicado_raw))
            except Exception as e:
                raise serializers.ValidationError(
                    {"descuento_aplicado": f"El descuento aplicado no es un número válido: {e}"})

        if not (Decimal('0.00') <= descuento_aplicado_value <= Decimal('1.00')):
            raise serializers.ValidationError(
                {"descuento_aplicado": "El descuento debe ser un valor entre 0.00 y 1.00."})

        data['descuento_aplicado'] = descuento_aplicado_value

        # === Validación y conversión del PRODUCTO ===
        producto_input = data.get('producto')

        if producto_input is None:  # Si el producto no se envió o es null
            raise serializers.ValidationError({"producto": "El producto es un campo requerido."})

        producto_obj = None
        if isinstance(producto_input, int):  # Si viene como ID, busca el objeto Producto
            try:
                producto_obj = Producto.objects.get(id=producto_input)
            except Producto.DoesNotExist:
                raise serializers.ValidationError({"producto": f"El producto con ID {producto_input} no existe."})
        elif isinstance(producto_input, Producto):  # Si ya es una instancia de Producto
            producto_obj = producto_input
        else:  # Formato de producto inválido
            raise serializers.ValidationError(
                {"producto": "Formato de producto inválido (debe ser un ID o un objeto Producto)."})

        data['producto'] = producto_obj  # Asegúrate de que los datos validados contengan el objeto Producto

        return data


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)
    usuario_nombre = serializers.CharField(source='usuario.first_name', read_only=True, allow_null=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    origen = serializers.CharField(read_only=True)  # <-- ¡NUEVO! Añadimos origen como campo de solo lectura

    class Meta:
        model = Venta
        fields = [
            'id', 'fecha', 'monto_total', 'usuario', 'usuario_nombre',
            'empresa', 'empresa_nombre', 'estado', 'origen', 'detalles'  # <-- Añade 'origen' aquí
        ]
        read_only_fields = ['monto_total', 'usuario_nombre', 'empresa_nombre',
                            'origen']  # <-- 'origen' también de solo lectura aquí

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')

        usuario_id = validated_data.pop('usuario')
        try:
            usuario_obj = CustomUser.objects.get(id=usuario_id)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"usuario": f"El usuario con ID {usuario_id} no existe."})
        validated_data['usuario'] = usuario_obj

        empresa_id = validated_data.pop('empresa')
        try:
            empresa_obj = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise serializers.ValidationError({"empresa": f"La empresa con ID {empresa_id} no existe."})
        validated_data['empresa'] = empresa_obj

        # Si el origen no se proporciona o no es válido, se usará el valor por defecto del modelo ('MANUAL')
        # Si se envía explícitamente desde el frontend (ej. 'MARKETPLACE'), validated_data lo tendrá.
        # No lo hacemos de solo lectura en la entrada porque el frontend lo enviará.
        # Para el serializer de salida sí será de solo lectura.

        with transaction.atomic():
            venta = Venta.objects.create(**validated_data)
            for detalle_data in detalles_data:
                DetalleVenta.objects.create(venta=venta, **detalle_data)

            venta.monto_total = venta.calculate_total_amount()
            venta.save(update_fields=['monto_total'])

        return venta

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', [])

        # Actualizar campos directos de Venta
        instance.fecha = validated_data.get('fecha', instance.fecha)
        instance.estado = validated_data.get('estado', instance.estado)
        instance.origen = validated_data.get('origen', instance.origen)  # <-- Permitir actualización de origen

        if 'usuario' in validated_data:
            usuario_data = validated_data.pop('usuario')
            if isinstance(usuario_data, int):
                try:
                    instance.usuario = CustomUser.objects.get(id=usuario_data)
                except CustomUser.DoesNotExist:
                    raise serializers.ValidationError({"usuario": f"El usuario con ID {usuario_data} no existe."})
            elif isinstance(usuario_data, CustomUser):
                instance.usuario = usuario_data
            else:
                raise serializers.ValidationError({"usuario": "Formato de usuario inválido."})

        if 'empresa' in validated_data:
            empresa_data = validated_data.pop('empresa')
            if isinstance(empresa_data, int):
                try:
                    instance.empresa = Empresa.objects.get(id=empresa_data)
                except Empresa.DoesNotExist:
                    raise serializers.ValidationError({"empresa": f"La empresa con ID {empresa_data} no existe."})
            elif isinstance(empresa_data, Empresa):
                instance.empresa = empresa_data
            else:
                raise serializers.ValidationError({"empresa": "Formato de empresa inválido."})

        instance.save()

        with transaction.atomic():
            existing_detail_map = {detalle.id: detalle for detalle in instance.detalles.all()}

            for detalle_data in detalles_data:
                detalle_id = detalle_data.get('id')

                producto_obj = detalle_data.get('producto')
                if not isinstance(producto_obj, Producto):
                    raise serializers.ValidationError({
                        "detalles": f"Error interno: El producto en el detalle no es un objeto Producto válido después de la validación. Detalle ID: {detalle_id}"
                    })

                if detalle_id:
                    if detalle_id in existing_detail_map:
                        detalle_instance = existing_detail_map.pop(detalle_id)
                        detalle_instance.producto = producto_obj
                        detalle_instance.cantidad = detalle_data.get('cantidad', detalle_instance.cantidad)
                        detalle_instance.precio_unitario = detalle_data.get('precio_unitario',
                                                                            detalle_instance.precio_unitario)
                        detalle_instance.descuento_aplicado = detalle_data.get('descuento_aplicado',
                                                                               detalle_instance.descuento_aplicado)
                        detalle_instance.save()
                    else:
                        raise serializers.ValidationError(
                            {"detalles": f"Detalle con ID {detalle_id} no encontrado o no pertenece a esta venta."})
                else:
                    existing_by_product = instance.detalles.filter(producto=producto_obj).first()

                    if existing_by_product:
                        detalle_instance = existing_by_product
                        existing_detail_map.pop(detalle_instance.id, None)
                        detalle_instance.producto = producto_obj
                        detalle_instance.cantidad = detalle_data.get('cantidad', detalle_instance.cantidad)
                        detalle_instance.precio_unitario = detalle_data.get('precio_unitario',
                                                                            detalle_instance.precio_unitario)
                        detalle_instance.descuento_aplicado = detalle_data.get('descuento_aplicado',
                                                                               detalle_instance.descuento_aplicado)
                        detalle_instance.save()
                    else:
                        DetalleVenta.objects.create(venta=instance, **detalle_data)

            for detalle_obj in existing_detail_map.values():
                detalle_obj.delete()

            instance.monto_total = instance.calculate_total_amount()
            instance.save(update_fields=['monto_total'])

        return instance
