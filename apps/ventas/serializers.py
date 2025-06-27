# apps/ventas/serializers.py

from rest_framework import serializers
from django.db import transaction
from apps.productos.models import Producto
from apps.usuarios.models import CustomUser
from apps.empresas.models import Empresa
from .models import Venta, DetalleVenta
from decimal import Decimal  # <--- ¡ESTA ES LA LÍNEA CRÍTICA A AÑADIR!


class DetalleVentaSerializer(serializers.ModelSerializer):
    # Field to display product name, read-only
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'descuento_aplicado']
        read_only_fields = ['producto_nombre']
        # Optionally, you can explicitly set 'producto' as required if not already by default:
        # extra_kwargs = {'producto': {'required': True}}

    def validate(self, data):
        # Retrieve and validate quantities and prices
        cantidad = data.get('cantidad')
        precio_unitario = data.get('precio_unitario')
        descuento_aplicado_raw = data.get('descuento_aplicado')

        # Validate 'cantidad'
        if not isinstance(cantidad, (int, float)) or cantidad <= 0:
            raise serializers.ValidationError({"cantidad": "La cantidad debe ser un número positivo."})

        # Validate and convert 'precio_unitario' to Decimal
        try:
            precio_unitario_decimal = Decimal(str(precio_unitario))
            if precio_unitario_decimal <= 0:
                raise serializers.ValidationError(
                    {"precio_unitario": "El precio unitario debe ser un número positivo."})
            data['precio_unitario'] = precio_unitario_decimal
        except Exception:
            raise serializers.ValidationError({"precio_unitario": "El precio unitario no es un número válido."})

        # Validate and convert 'descuento_aplicado' to Decimal
        descuento_aplicado_value = Decimal('0.0000')  # Default to 0 if not provided or empty
        if descuento_aplicado_raw is not None and str(descuento_aplicado_raw).strip() != '':
            try:
                descuento_aplicado_value = Decimal(str(descuento_aplicado_raw))
            except Exception as e:
                raise serializers.ValidationError(
                    {"descuento_aplicado": f"El descuento aplicado no es un número válido: {e}"})

        if not (Decimal('0.00') <= descuento_aplicado_value <= Decimal('1.00')):
            raise serializers.ValidationError(
                {"descuento_aplicado": "El descuento debe ser un valor entre 0.00 y 1.00."})

        data['descuento_aplicado'] = descuento_aplicado_value

        # Validate and convert 'producto' (ForeignKey) to a Product object instance
        producto_input = data.get('producto')

        if producto_input is None:
            raise serializers.ValidationError({"producto": "El producto es un campo requerido."})

        producto_obj = None
        if isinstance(producto_input, int):  # If it comes as an ID, fetch the Product object
            try:
                producto_obj = Producto.objects.get(id=producto_input)
            except Producto.DoesNotExist:
                raise serializers.ValidationError({"producto": f"El producto con ID {producto_input} no existe."})
        elif isinstance(producto_input, Producto):  # If it's already a Product instance
            producto_obj = producto_input
        else:  # Invalid product format
            raise serializers.ValidationError(
                {"producto": "Formato de producto inválido (debe ser un ID o un objeto Producto)."})

        data['producto'] = producto_obj  # Ensure validated data contains the Product object

        return data


class VentaSerializer(serializers.ModelSerializer):
    # Use PrimaryKeyRelatedField for ForeignKey relationships to expect IDs
    # and let DRF handle object conversion.
    usuario = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    empresa = serializers.PrimaryKeyRelatedField(queryset=Empresa.objects.all())

    # Nested serializer for sale details
    detalles = DetalleVentaSerializer(many=True)

    # Read-only fields to display related object names
    usuario_nombre = serializers.CharField(source='usuario.first_name', read_only=True, allow_null=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id', 'fecha', 'monto_total', 'usuario', 'usuario_nombre',
            'empresa', 'empresa_nombre', 'estado', 'detalles'
        ]
        # 'monto_total' is calculated, not sent from the frontend, and other name fields are read-only
        read_only_fields = ['monto_total', 'usuario_nombre', 'empresa_nombre']

    def create(self, validated_data):
        # Pop 'detalles' data, as they are handled separately
        detalles_data = validated_data.pop('detalles')

        # 'usuario' and 'empresa' are already object instances due to PrimaryKeyRelatedField
        # So, no manual fetching is needed here.

        with transaction.atomic():
            # Create the Venta instance
            venta = Venta.objects.create(**validated_data)

            # Create associated DetalleVenta instances
            for detalle_data in detalles_data:
                # 'detalle_data['producto']' is already a Product object instance
                # because it was validated and converted by DetalleVentaSerializer's validate method.
                DetalleVenta.objects.create(venta=venta, **detalle_data)

            # Calculate and update the total amount of the sale
            venta.monto_total = venta.calculate_total_amount()
            venta.save(update_fields=['monto_total'])  # Save only the updated field

        return venta

    def update(self, instance, validated_data):
        # Pop 'detalles' data for separate handling
        detalles_data = validated_data.pop('detalles', [])

        # Update direct fields of Venta instance
        instance.fecha = validated_data.get('fecha', instance.fecha)
        instance.estado = validated_data.get('estado', instance.estado)

        # Update 'usuario' and 'empresa' if they are present in validated_data.
        # They will already be object instances thanks to PrimaryKeyRelatedField.
        if 'usuario' in validated_data:
            instance.usuario = validated_data['usuario']
        if 'empresa' in validated_data:
            instance.empresa = validated_data['empresa']

        instance.save()  # Save the updated direct fields of the Venta

        with transaction.atomic():
            # Create a map of existing detail IDs for efficient lookup and removal tracking
            existing_detail_map = {detalle.id: detalle for detalle in instance.detalles.all()}

            # Process each detail received from the frontend
            for detalle_data in detalles_data:
                detalle_id = detalle_data.get('id')

                # 'producto' in 'detalle_data' should already be a Product object instance
                # due to validation in DetalleVentaSerializer.
                producto_obj = detalle_data.get('producto')
                if not isinstance(producto_obj, Producto):
                    raise serializers.ValidationError({
                        "detalles": f"Internal Error: Product in detail is not a valid Product object after validation. Detail ID: {detalle_id}"
                    })

                if detalle_id:  # If detail has an ID, it's an existing detail to be updated
                    if detalle_id in existing_detail_map:
                        detalle_instance = existing_detail_map.pop(detalle_id)  # Remove from map as it's processed
                        # Update existing detail fields
                        detalle_instance.producto = producto_obj  # Direct assignment as it's already an object
                        detalle_instance.cantidad = detalle_data.get('cantidad', detalle_instance.cantidad)
                        detalle_instance.precio_unitario = detalle_data.get('precio_unitario',
                                                                            detalle_instance.precio_unitario)
                        detalle_instance.descuento_aplicado = detalle_data.get('descuento_aplicado',
                                                                               detalle_instance.descuento_aplicado)
                        detalle_instance.save()
                    else:
                        # If an ID is provided but doesn't belong to this sale, it's an error
                        raise serializers.ValidationError(
                            {"detalles": f"Detalle con ID {detalle_id} no encontrado o no pertenece a esta venta."})
                else:  # If detail has no ID, it's either a new detail or an existing one sent without ID

                    # Try to find an existing detail for this product in this sale
                    existing_by_product = instance.detalles.filter(producto=producto_obj).first()

                    if existing_by_product:
                        # If a detail with this product already exists for this sale, update it
                        detalle_instance = existing_by_product
                        existing_detail_map.pop(detalle_instance.id, None)  # Remove from map if it was there
                        detalle_instance.producto = producto_obj  # Direct assignment
                        detalle_instance.cantidad = detalle_data.get('cantidad', detalle_instance.cantidad)
                        detalle_instance.precio_unitario = detalle_data.get('precio_unitario',
                                                                            detalle_instance.precio_unitario)
                        detalle_instance.descuento_aplicado = detalle_data.get('descuento_aplicado',
                                                                               detalle_instance.descuento_aplicado)
                        detalle_instance.save()
                    else:
                        # If no existing detail for this product, create a new one
                        DetalleVenta.objects.create(venta=instance, **detalle_data)

            # Any remaining details in existing_detail_map were not sent in the update request, so delete them
            for detalle_obj in existing_detail_map.values():
                detalle_obj.delete()

            # Recalculate and save the total amount of the sale after all detail modifications
            instance.monto_total = instance.calculate_total_amount()
            instance.save(update_fields=['monto_total'])

        return instance
