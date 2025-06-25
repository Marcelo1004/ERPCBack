from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction

# Asegúrate de que estos imports sean correctos para la ubicación de tus modelos
from .models import User
from apps.empresas.models import Empresa
from apps.empresas.serializers import \
    EmpresaSerializer  # Asegúrate de que EmpresaSerializer esté definido y sea accesible
from apps.suscripciones.models import Suscripcion


# from apps.suscripciones.serializers import SuscripcionSerializer # No se usa directamente aquí


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
    # empresa_detail se usa para anidar los detalles de la empresa al leer
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'telefono', 'ci', 'direccion',
            'empresa',  # ID de la FK, puede ser leído y escrito para asignar una empresa existente
            'empresa_detail',  # Detalles de la empresa (solo lectura, anidado)
            'is_active', 'is_staff', 'is_superuser',
            'date_joined',  # Campo generado por Django, solo lectura
            'last_login'  # Campo generado por Django, solo lectura
        ]
        read_only_fields = [
            'id', 'username', 'email', 'date_joined', 'last_login',
            'is_active', 'is_staff', 'is_superuser'
        ]  # Se eliminó 'empresa' de read_only_fields para permitir su actualización


# Serializer para el registro de usuarios (creación)
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

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
        model = User
        # Estos son los campos que se ESPERA recibir del frontend para el REGISTRO
        fields = [
            'username', 'email', 'first_name', 'last_name', 'role',
            'telefono', 'ci', 'direccion',
            'password', 'password2',
            'empresa',  # Para asignar un usuario a una empresa EXISTENTE
            'empresa_nombre',  # Para SuperUsuario que crea una nueva empresa
            'empresa_nit',  # Para SuperUsuario que crea una nueva empresa
            'suscripcion_id'  # Para SuperUsuario que crea una nueva empresa
        ]
        # read_only_fields aquí son campos del modelo User que no pueden ser modificados
        # directamente al crearlos (Django los gestiona), pero pueden ser leídos después.
        # Los campos `write_only` definidos arriba no necesitan estar en `read_only_fields`
        # porque su naturaleza `write_only` ya implica que no se leerán.
        read_only_fields = [
            'id', 'is_active', 'is_staff', 'is_superuser',
            'date_joined',
            'last_login'
        ]

        # extra_kwargs para configurar requisitos y valores por defecto
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'ci': {'required': True},
            'telefono': {'required': False, 'allow_null': True},  # Explicitamente opcional y nulo
            'direccion': {'required': False, 'allow_null': True},  # Explicitamente opcional y nulo
            'role': {'required': False, 'default': 'CLIENTE'},  # Rol por defecto si no se especifica
            'empresa': {'required': False, 'allow_null': True},
            # Empresa es opcional al registro, pero validado después
        }

    def validate(self, attrs):
        # 1. Validar contraseñas
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})

        # 2. Validar que el rol no sea 'SUPERUSER' para registro directo
        if attrs.get('role') == 'SUPERUSER':
            raise serializers.ValidationError({"role": "No se permite el registro directo como Super Usuario."})

        empresa_nombre = attrs.get('empresa_nombre')
        empresa_nit = attrs.get('empresa_nit')
        suscripcion_id = attrs.get('suscripcion_id')
        user_role = attrs.get('role', 'CLIENTE')  # Obtener el rol, por defecto 'CLIENTE'

        # Lógica de validación de empresa para SuperUsuarios (creando nueva empresa)
        # Esto ocurre si el SuperUsuario envía datos de empresa (nombre o nit o suscripcion_id)
        if self.context['request'].user and self.context['request'].user.is_superuser:
            # Si se intenta crear una nueva empresa (alguno de los campos está presente)
            if empresa_nombre or empresa_nit or suscripcion_id:
                if not empresa_nombre or not empresa_nit or not suscripcion_id:
                    raise serializers.ValidationError(
                        {
                            "empresa_data": "Nombre de empresa, NIT y ID de suscripción son requeridos para crear una nueva empresa."}
                    )
                # Validar unicidad de nombre y NIT para nuevas empresas
                if Empresa.objects.filter(nombre=empresa_nombre).exists():
                    raise serializers.ValidationError(
                        {"empresa_nombre": "Ya existe una empresa con este nombre."}
                    )
                if Empresa.objects.filter(nit=empresa_nit).exists():
                    raise serializers.ValidationError(
                        {"empresa_nit": "Ya existe una empresa con este NIT/RUC."}
                    )
                # Si un superusuario crea una empresa, el rol del usuario asignado como admin_empresa
                # DEBE ser ADMINISTRATIVO o CLIENTE (si es un cliente que luego se actualiza su rol)
                if user_role not in ['CLIENTE', 'ADMINISTRATIVO']:
                    raise serializers.ValidationError(
                        {"role": "El rol debe ser 'CLIENTE' o 'ADMINISTRATIVO' si se registra una nueva empresa."}
                    )
                # Si el superusuario crea una empresa, el campo 'empresa' (FK a Empresa)
                # en el usuario NO debe ser enviado, porque la empresa se creará.
                if attrs.get('empresa'):
                    raise serializers.ValidationError(
                        {"empresa": "No se puede asignar a una empresa existente al crear una nueva empresa."})

        # Lógica de validación para ADMINISTRATIVOS o EMPLEADOS que crean usuarios
        # (Deben asociar el usuario a su propia empresa, si el rol no es 'CLIENTE')
        elif not self.context['request'].user.is_superuser:  # Si no es SuperUsuario
            # Si el rol es diferente de 'CLIENTE'
            if user_role != 'CLIENTE':
                request_user = self.context['request'].user
                if not request_user.empresa:
                    raise serializers.ValidationError({
                                                          "role": "Solo un administrador de empresa puede crear usuarios con roles diferentes a 'CLIENTE'."})

                # Si el admin de empresa envía una empresa_id, debe ser su propia empresa.
                if attrs.get('empresa') and attrs['empresa'].id != request_user.empresa.id:
                    raise serializers.ValidationError(
                        {"empresa": "No tienes permiso para crear usuarios en otra empresa."})

                # Si el admin de empresa NO envía una empresa_id, se la asignamos automáticamente.
                if not attrs.get('empresa'):
                    attrs['empresa'] = request_user.empresa

            # Si el rol es 'CLIENTE' y se envían datos de empresa_nombre o empresa_nit
            if user_role == 'CLIENTE' and (empresa_nombre or empresa_nit or suscripcion_id):
                raise serializers.ValidationError(
                    {"empresa_data": "No se pueden proporcionar datos de empresa al crear un cliente."})

            # Si no es SuperUser y el rol no es 'CLIENTE', la empresa es obligatoria
            if user_role != 'CLIENTE' and not attrs.get('empresa'):
                # Esta validación debería ser cubierta por la lógica anterior, pero como fallback
                raise serializers.ValidationError(
                    {"empresa": "Para roles diferentes a 'CLIENTE', la cuenta debe ser asignada a una empresa."})

        # Si el usuario no es superuser ni administrador, y el rol no es 'CLIENTE', entonces error
        # Esta validación ya la cubre la del `if user_role != 'CLIENTE'` de arriba.

        # Asegurarse que los campos de nueva empresa no se envíen si el rol es CLIENTE
        if user_role == 'CLIENTE' and (empresa_nombre or empresa_nit or suscripcion_id):
            raise serializers.ValidationError(
                {"empresa_data": "No se pueden proporcionar datos de empresa al crear un cliente."})

        # Eliminar campos de empresa si no son relevantes para el tipo de creación
        # Esto es importante para que super().validate no falle si los campos no van al modelo User
        if not (self.context['request'].user and self.context['request'].user.is_superuser and (
                empresa_nombre or empresa_nit or suscripcion_id)):
            attrs.pop('empresa_nombre', None)
            attrs.pop('empresa_nit', None)
            attrs.pop('suscripcion_id', None)

        return super().validate(attrs)

    def create(self, validated_data):
        with transaction.atomic():  # Asegura que la creación de usuario y empresa sea atómica

            validated_data.pop('password2')  # 'password2' solo es para validación, no para guardar

            empresa = validated_data.pop('empresa', None)  # Podría ser un objeto Empresa si lo asignó un admin
            empresa_nombre = validated_data.pop('empresa_nombre', None)
            empresa_nit = validated_data.pop('empresa_nit', None)
            suscripcion_id = validated_data.pop('suscripcion_id', None)  # ID de suscripción para la nueva empresa

            # Crea el usuario primero con los datos directamente para el modelo CustomUser
            user = User.objects.create(
                username=validated_data['username'],
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                role=validated_data.get('role', 'CLIENTE'),
                telefono=validated_data.get('telefono'),
                ci=validated_data.get('ci'),
                direccion=validated_data.get('direccion'),
                # La empresa se asignará después si es una nueva o si fue asignada por un admin
            )
            user.set_password(validated_data['password'])

            # Asigna la empresa si ya existe y fue asignada (por un admin de empresa)
            if empresa:
                user.empresa = empresa

            # Lógica para crear una nueva empresa si el SuperUsuario lo indicó
            if empresa_nombre and empresa_nit and suscripcion_id:
                try:
                    suscripcion_obj = Suscripcion.objects.get(id=suscripcion_id)
                    new_empresa = Empresa.objects.create(
                        nombre=empresa_nombre,
                        nit=empresa_nit,
                        suscripcion=suscripcion_obj,
                        admin_empresa=user  # Asignar el usuario recién creado como admin de esta nueva empresa
                    )
                    user.empresa = new_empresa  # Asignar el usuario a la nueva empresa
                except Suscripcion.DoesNotExist:
                    # Esto debería ser capturado por la validación, pero como fallback
                    raise serializers.ValidationError({"suscripcion_id": "La suscripción seleccionada no existe."})

            user.save()  # Guardar el usuario con su contraseña y la empresa asignada
        return user


# Serializer para la actualización de usuarios por parte de un administrador
class AdminUserUpdateSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), required=False, allow_null=True
    )
    # Para mostrar los detalles de la empresa en la respuesta (read_only)
    empresa_detail = EmpresaSerializer(source='empresa', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'telefono', 'ci', 'direccion', 'is_active', 'is_staff', 'is_superuser',
            'empresa', 'empresa_detail',
            'date_joined',  # Incluir para que sea parte de la representación aunque sea read_only
            'last_login'  # Incluir para que sea parte de la representación aunque sea read_only
        ]
        # Campos que no pueden ser modificados por este serializador (generalmente los IDs y campos auto-gestionados)
        read_only_fields = [
            'id', 'username', 'email', 'date_joined', 'last_login',
            'is_active', 'is_staff', 'is_superuser'
        ]

    def validate(self, attrs):
        current_user = self.instance  # El objeto de usuario que se está actualizando
        request_user = self.context['request'].user  # El usuario que hace la petición

        new_role = attrs.get('role', current_user.role)
        new_empresa = attrs.get('empresa', current_user.empresa)

        # 1. Validación de Super_Usuario y empresa
        if new_role == 'SUPERUSER' and new_empresa:
            raise serializers.ValidationError(
                {"empresa": "Un Super_Usuario no debe estar asignado a una empresa específica."}
            )

        # 2. Validación: Si el rol no es Super_Usuario, debe tener una empresa asignada
        if new_role != 'SUPERUSER' and not new_empresa:
            raise serializers.ValidationError(
                {"empresa": "Un usuario que no es Super_Usuario debe estar asignado a una empresa."}
            )

        # 3. Validar permisos de asignación de empresa para no-SuperUsuarios
        if not request_user.is_superuser:  # Si quien actualiza NO es Super_Usuario
            if new_empresa and new_empresa.id != request_user.empresa.id:
                raise serializers.ValidationError(
                    {"empresa": "No tienes permiso para asignar usuarios a otra empresa."})

            # Si el rol cambia de CLIENTE a otro (ADMINISTRATIVO/EMPLEADO)
            if current_user.role == 'CLIENTE' and new_role != 'CLIENTE':
                # Y no tiene empresa asignada (lo cual debería ser obligatorio por la validación 2)
                if not new_empresa:
                    raise serializers.ValidationError(
                        {"empresa": "Para asignar un rol de empresa, el usuario debe estar asignado a una empresa."}
                    )
                # Y la empresa asignada no es la del administrador que lo modifica
                if new_empresa.id != request_user.empresa.id:
                    raise serializers.ValidationError({"empresa": "Solo puedes asignar usuarios a tu propia empresa."})

        return attrs

    def update(self, instance, validated_data):
        # Manejo especial para la contraseña si se envía (no está en 'fields' por seguridad)
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # Actualiza el resto de campos validados
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance