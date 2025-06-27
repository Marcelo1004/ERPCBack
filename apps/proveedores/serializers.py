from rest_framework import serializers
from .models import Proveedor
# Importa el EmpresaSerializer que acabas de crear o confirmar
from apps.empresas.serializers import EmpresaSerializer


class ProveedorSerializer(serializers.ModelSerializer):
    # Esto serializará el objeto ForeignKey 'empresa' usando EmpresaSerializer
    # y lo asignará al campo 'empresa_detail' en la respuesta JSON.
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    # Si aún tenías 'contacto', 'email', 'telefono' en tu `Proveedor` model
    # después de mi sugerencia anterior, por favor, asegúrate de que tu modelo
    # ahora tenga 'contacto_nombre', 'contacto_email', 'contacto_telefono'.
    # Si no, ajusta el modelo y la base de datos primero.
    # Asumo que ya los corregiste en el modelo y el frontend.

    class Meta:
        model = Proveedor
        fields = [
            'id', 'nombre', 'contacto_nombre', 'contacto_email',
            'contacto_telefono', 'direccion', 'nit', 'activo',
            'fecha_creacion', 'fecha_actualizacion',
            'empresa',  # Campo FK (ID) que el frontend envía y el backend espera para guardar
            'empresa_detail'  # Campo anidado (objeto) que el frontend lee para mostrar
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion', 'empresa_detail']
        # 'empresa' (el ID de la FK) sigue siendo escribible, ya que lo necesitas para crear/actualizar.