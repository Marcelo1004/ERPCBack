# apps/users/serializers.py

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction

# === CAMBIO CLAVE AQUÍ: Importa la CLASE de tu modelo de usuario (ej. CustomUser) ===
# Asumo que tu modelo de usuario se llama CustomUser. Si tiene otro nombre (ej. MyUser),
# cámbialo a from .models import MyUser as User
from .models import CustomUser as User  # <--- CORREGIDO: Importa el modelo, no el gestor
# ====================================================================================

from apps.empresas.models import Empresa
from apps.empresas.serializers import EmpresaSerializer
from apps.suscripciones.models import Suscripcion

# === NUEVAS IMPORTACIONES PARA RBAC ===
from apps.rbac.models import Role, Permission  # Importa los modelos Role y Permission
from apps.rbac.serializers import RoleSerializer  # Importa RoleSerializer para anidar


# =======================================

# Serializer para el token JWT personalizado
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        serializer = UserProfileSerializer(user)
        data['user'] = serializer.data
        return data


# Serializer para el perfil de usuario (lectura, uso en el login)
class UserProfileSerializer(serializers.ModelSerializer):
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    # 'role' ahora es un serializador anidado para mostrar el objeto completo del rol (id, name, description, etc.)
    role = RoleSerializer(read_only=True)

    class Meta:
        model = User  # Esto ahora apuntará correctamente a la clase CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'telefono', 'ci', 'direccion',
            'empresa',
            'empresa_detail',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined',
            'last_login'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'date_joined', 'last_login',
            'is_active', 'is_staff', 'is_superuser', 'role'
        ]


# Serializer para el registro de usuarios (creación)
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    # 'role' acepta un ID de Role para escritura. El queryset asegura que solo se puedan asignar roles existentes.
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, allow_null=True
    )

    # Campos write_only para la creación de una NUEVA empresa por SuperUsuarios
    empresa_nombre = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=100,
        help_text="Solo si crea una nueva empresa (para SuperUsuarios)."
    )
    empresa_nit = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=50,
        help_text="NIT de la nueva empresa (para SuperUsuarios)."
    )
    suscripcion_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True,
        help_text="ID de suscripción para la nueva empresa (para SuperUsuarios)."
    )

    class Meta:
        model = User  # Esto ahora apuntará correctamente a la clase CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name', 'role',
            'telefono', 'ci', 'direccion',
            'password', 'password2',
            'empresa',
            'empresa_nombre',
            'empresa_nit',
            'suscripcion_id'
        ]
        read_only_fields = [
            'id', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'ci': {'required': True},
            'telefono': {'required': False, 'allow_null': True},
            'direccion': {'required': False, 'allow_null': True},
            'empresa': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        # 1. Validar contraseñas
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})

        # Obtener el rol. Si viene como ID, PrimaryKeyRelatedField ya lo convierte a instancia en attrs.
        user_role_instance = attrs.get('role')

        # Si no se proporciona rol, intenta asignar el rol 'Cliente' por defecto
        if user_role_instance is None:
            try:
                default_client_role = Role.objects.get(name='Cliente')
                attrs['role'] = default_client_role
                user_role_instance = default_client_role
            except Role.DoesNotExist:
                raise serializers.ValidationError(
                    {"role": "El rol 'Cliente' por defecto no existe. Por favor, créalo en el administrador."})

        # 2. Validar que el rol no sea 'Super Usuario' para registro directo
        if user_role_instance.name == 'Super Usuario':
            raise serializers.ValidationError({"role": "No se permite el registro directo como Super Usuario."})

        empresa_nombre = attrs.get('empresa_nombre')
        empresa_nit = attrs.get('empresa_nit')
        suscripcion_id = attrs.get('suscripcion_id')

        # Lógica de validación de empresa para SuperUsuarios (creando nueva empresa)
        if self.context['request'].user and self.context['request'].user.is_superuser:
            if empresa_nombre or empresa_nit or suscripcion_id:
                if not empresa_nombre or not empresa_nit or not suscripcion_id:
                    raise serializers.ValidationError(
                        {
                            "empresa_data": "Nombre de empresa, NIT y ID de suscripción son requeridos para crear una nueva empresa."}
                    )
                if Empresa.objects.filter(nombre=empresa_nombre).exists():
                    raise serializers.ValidationError({"empresa_nombre": "Ya existe una empresa con este nombre."})
                if Empresa.objects.filter(nit=empresa_nit).exists():
                    raise serializers.ValidationError({"empresa_nit": "Ya existe una empresa con este NIT/RUC."})

                if user_role_instance.name not in ['Cliente', 'Administrador']:
                    raise serializers.ValidationError(
                        {"role": "El rol debe ser 'Cliente' o 'Administrador' si se registra una nueva empresa."}
                    )
                if attrs.get('empresa'):
                    raise serializers.ValidationError(
                        {"empresa": "No se puede asignar a una empresa existente al crear una nueva empresa."}
                    )

        # Lógica de validación para ADMINISTRATIVOS o EMPLEADOS que crean usuarios
        elif not self.context['request'].user.is_superuser:
            if user_role_instance.name != 'Cliente':
                request_user = self.context['request'].user
                # Es importante verificar que el usuario tenga una empresa asociada para que pueda crear otros usuarios de empresa
                if not (hasattr(request_user, 'empresa') and request_user.empresa):
                    raise serializers.ValidationError({
                        "role": "Solo un administrador de empresa puede crear usuarios con roles diferentes a 'Cliente'."})

                # Si intenta asignar una empresa, debe ser la suya.
                if attrs.get('empresa') and attrs['empresa'].id != request_user.empresa.id:
                    raise serializers.ValidationError(
                        {"empresa": "No tienes permiso para crear usuarios en otra empresa."}
                    )
                # Si el admin de empresa NO envía una empresa_id, se la asignamos automáticamente.
                if not attrs.get('empresa'):
                    attrs['empresa'] = request_user.empresa

            # Si el rol es 'Cliente' y se envían datos de empresa_nombre o empresa_nit
            if user_role_instance.name == 'Cliente' and (empresa_nombre or empresa_nit or suscripcion_id):
                raise serializers.ValidationError(
                    {"empresa_data": "No se pueden proporcionar datos de empresa al crear un cliente."}
                )

            # Para roles que no son 'Cliente', la cuenta debe estar asignada a una empresa
            if user_role_instance.name != 'Cliente' and not attrs.get('empresa'):
                raise serializers.ValidationError(
                    {"empresa": "Para roles diferentes a 'Cliente', la cuenta debe ser asignada a una empresa."}
                )

        # Asegurarse que los campos de nueva empresa no se envíen si el rol es CLIENTE
        if user_role_instance.name == 'Cliente' and (empresa_nombre or empresa_nit or suscripcion_id):
            raise serializers.ValidationError(
                {"empresa_data": "No se pueden proporcionar datos de empresa al crear un cliente."}
            )

        # Eliminar campos de empresa si no son relevantes para el tipo de creación
        if not (self.context['request'].user and self.context['request'].user.is_superuser and (
                empresa_nombre or empresa_nit or suscripcion_id)):
            attrs.pop('empresa_nombre', None)
            attrs.pop('empresa_nit', None)
            attrs.pop('suscripcion_id', None)

        return super().validate(attrs)

    def create(self, validated_data):
        with transaction.atomic():
            validated_data.pop('password2')

            empresa_instance = validated_data.pop('empresa', None)  # Renombrado para claridad
            empresa_nombre = validated_data.pop('empresa_nombre', None)
            empresa_nit = validated_data.pop('empresa_nit', None)
            suscripcion_id = validated_data.pop('suscripcion_id', None)

            role_instance = validated_data.pop('role', None)

            user = User.objects.create(
                username=validated_data['username'],
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                role=role_instance,  # Asigna la instancia del rol directamente
                telefono=validated_data.get('telefono'),
                ci=validated_data.get('ci'),
                direccion=validated_data.get('direccion'),
            )
            user.set_password(validated_data['password'])

            if empresa_instance:  # Usar la instancia de empresa existente si se proporcionó
                user.empresa = empresa_instance

            if empresa_nombre and empresa_nit and suscripcion_id:
                try:
                    suscripcion_obj = Suscripcion.objects.get(id=suscripcion_id)
                    new_empresa = Empresa.objects.create(
                        nombre=empresa_nombre,
                        nit=empresa_nit,
                        suscripcion=suscripcion_obj,
                        admin_empresa=user
                    )
                    user.empresa = new_empresa
                except Suscripcion.DoesNotExist:
                    raise serializers.ValidationError({"suscripcion_id": "La suscripción seleccionada no existe."})

            user.save()
        return user


# Serializer para la actualización de usuarios por parte de un administrador
class AdminUserUpdateSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), required=False, allow_null=True
    )
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    # 'role' acepta un ID de Role para escritura
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, allow_null=True
    )

    # Campo opcional para cambio de contraseña
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'telefono', 'ci', 'direccion', 'is_active', 'is_staff', 'is_superuser',
            'empresa', 'empresa_detail',
            'date_joined',
            'last_login',
            'password',  # Incluir aquí para que el serializer lo procese
            'password2',  # Incluir aquí para que el serializer lo procese
        ]
        read_only_fields = [
            'id', 'username', 'email', 'date_joined', 'last_login',
        ]
        # is_active, is_staff, is_superuser ya no son read_only aquí porque un superuser los puede cambiar.
        # El control de permisos para estos campos se maneja en las vistas o en el método validate.

    def validate(self, attrs):
        current_user = self.instance  # El usuario que se está actualizando
        request_user = self.context['request'].user  # El usuario que realiza la solicitud

        # Validar contraseñas si se proporcionan
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password or password2:
            if password != password2:
                raise serializers.ValidationError({"password": "Las nuevas contraseñas no coinciden."})
            if not password:  # Si se proporciona password2 pero no password
                raise serializers.ValidationError({"password": "Debe proporcionar una nueva contraseña."})
            # Removemos password2 porque no se guarda en el modelo directamente
            attrs.pop('password2', None)

        # Obtener el nuevo rol. Si no se proporciona en attrs, usar el rol actual del usuario.
        # `attrs.get('role')` ya es la instancia del Role gracias a PrimaryKeyRelatedField
        new_role_instance = attrs.get('role', current_user.role)

        # Validar que `new_role_instance` no sea `None` si `role` fue proporcionado en `attrs`
        # pero `PrimaryKeyRelatedField` no encontró un objeto Role válido (ej. ID inexistente)
        if attrs.get('role') is not None and new_role_instance is None:
            raise serializers.ValidationError({"role": "El ID de rol proporcionado no es válido."})

        new_empresa_instance = attrs.get('empresa', current_user.empresa)  # Obtener la instancia de empresa

        # 1. Validación de Super_Usuario y empresa
        if new_role_instance and new_role_instance.name == 'Super Usuario' and new_empresa_instance:
            raise serializers.ValidationError(
                {"empresa": "Un Super Usuario no debe estar asignado a una empresa específica."}
            )

        # 2. Validación: Si el rol no es 'Super Usuario', debe tener una empresa asignada
        if new_role_instance and new_role_instance.name != 'Super Usuario' and not new_empresa_instance:
            raise serializers.ValidationError(
                {"empresa": "Un usuario que no es Super Usuario debe estar asignado a una empresa."}
            )

        # 3. Validar permisos de asignación de empresa y flags de usuario para no-SuperUsuarios
        if not request_user.is_superuser:
            # Un administrador de empresa NO puede cambiar el rol de Super Usuario
            if new_role_instance and new_role_instance.name == 'Super Usuario' and new_role_instance != current_user.role:
                raise serializers.ValidationError(
                    {"role": "Solo un Super Usuario puede asignar el rol 'Super Usuario'."})

            # Un administrador de empresa NO puede desasignar el rol de Super Usuario de otro usuario
            if current_user.role and current_user.role.name == 'Super Usuario' and (
                    not new_role_instance or new_role_instance.name != 'Super Usuario'
            ):
                raise serializers.ValidationError({
                    "role": "Solo un Super Usuario puede modificar o eliminar el rol 'Super Usuario' de otro usuario."})

            # Un administrador de empresa solo puede modificar usuarios de SU propia empresa
            # Y no puede cambiar la empresa de un usuario
            if current_user.empresa and request_user.empresa and current_user.empresa.id != request_user.empresa.id:
                raise serializers.ValidationError(
                    {"detail": "No tienes permiso para modificar usuarios de otra empresa."}
                )
            # Asegura que no se intente cambiar la empresa si no es superusuario
            if new_empresa_instance and request_user.empresa and new_empresa_instance.id != request_user.empresa.id:
                raise serializers.ValidationError(
                    {"empresa": "No tienes permiso para asignar usuarios a otra empresa."}
                )
            # Además, si el request_user no es superuser, no pueden cambiar 'is_active', 'is_staff', 'is_superuser'
            # y estas propiedades deben ser eliminadas de attrs si se intentan cambiar
            if 'is_active' in attrs and attrs['is_active'] != current_user.is_active:
                raise serializers.ValidationError(
                    {"is_active": "Solo un Super Usuario puede cambiar el estado de actividad."})
            if 'is_staff' in attrs and attrs['is_staff'] != current_user.is_staff:
                raise serializers.ValidationError(
                    {"is_staff": "Solo un Super Usuario puede cambiar el estado de staff."})
            if 'is_superuser' in attrs and attrs['is_superuser'] != current_user.is_superuser:
                raise serializers.ValidationError(
                    {"is_superuser": "Solo un Super Usuario puede cambiar el estado de superusuario."})

        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # Si el rol se ha actualizado, PrimaryKeyRelatedField ya lo convierte a instancia
        # Así que simplemente se asigna
        # validated_data.pop('password2', None) ya se hizo en validate

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance