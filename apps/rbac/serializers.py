from rest_framework import serializers
from .models import Permission, Role


class PermissionSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Permission.
    """
    class Meta:
        model = Permission
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
        extra_kwargs = {
            'name': {'error_messages': {'required': 'El nombre del permiso es requerido.'}},
            'code_name': {'error_messages': {'required': 'El código del permiso es requerido.'}},
        }

class RoleSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Role.
    Incluye los permisos anidados para LECTURA.
    Y un campo para la ESCRITURA de IDs de permisos.
    """
    # Campo para LECTURA: Muestra los detalles completos de los permisos asociados al rol.
    permissions = PermissionSerializer(many=True, read_only=True)

    # Campo para ESCRITURA: Acepta una lista de IDs de permisos al crear/actualizar un rol.
    # El `source='permissions'` le dice a DRF que este campo maneja el ManyToManyField 'permissions' del modelo.
    # El `write_only=True` asegura que este campo solo se use para la entrada de datos (POST/PUT/PATCH), no para la salida (GET).
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), # Asegura que solo IDs de permisos existentes sean válidos
        many=True,
        source='permissions', # Mapea los IDs recibidos al ManyToManyField 'permissions'
        write_only=True,
        required=False # Opcional: si los permisos no son obligatorios al crear/actualizar un rol
    )

    class Meta:
        model = Role
        fields = '__all__' # Esto incluirá 'permissions' (lectura) y 'permission_ids' (escritura)
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
        extra_kwargs = {
            'name': {'error_messages': {'required': 'El nombre del rol es requerido.'}},
        }

# apps/rbac/urls.py (sin cambios, ya lo analizamos)
# ...

# Si tu UserSerializer está en apps/users/serializers.py, asegúrate de que también maneje el campo 'role'
# para aceptar IDs en la escritura, similar a cómo se hizo con 'permission_ids' aquí, o usar RoleAssignmentSerializer
# como ya habías sugerido.