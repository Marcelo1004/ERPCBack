# apps/usuarios/models.py

from apps.rbac.models import Role  # Importa el modelo Role
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from apps.empresas.models import Empresa  # Importa el modelo Empresa


class CustomUserManager(BaseUserManager):
    """
    Manager de modelo de usuario personalizado donde el username es el identificador principal
    y el email es un campo requerido.
    """

    def create_user(self, username, email, password=None,
                    **extra_fields):  # El orden de los argumentos coincide con REQUIRED_FIELDS
        if not email:
            raise ValueError('El campo Email debe ser establecido')
        if not username:
            raise ValueError('El campo Username debe ser establecido')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None,
                         **extra_fields):  # El orden de los argumentos coincide con REQUIRED_FIELDS
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario debe tener is_superuser=True.')

        # Intentar obtener el rol 'Super Usuario'
        try:
            superuser_role_obj = Role.objects.get(name='Super Usuario')
        except Role.DoesNotExist:
            raise ValueError(
                "El rol 'Super Usuario' no existe. Asegúrate de que este rol se haya creado en tu seeder (apps/rbac/signals.py) antes de intentar crear un superusuario."
            )

        # Asigna la instancia del rol al campo 'role'
        extra_fields['role'] = superuser_role_obj

        # Crea el superusuario usando create_user
        return self.create_user(username, email, password, **extra_fields)


# Renombra la clase a CustomUser para consistencia con AUTH_USER_MODEL en settings.py y otros archivos
class CustomUser(AbstractUser):

    email = models.EmailField(unique=True, blank=False, null=False)  # Hacerlo unique y no nulo

    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users',
                             verbose_name="Rol del Usuario")

    telefono = models.CharField(max_length=15, blank=True, null=True)
    ci = models.CharField(max_length=20, unique=True, blank=True,
                          null=True)  # unique=True si es realmente único a nivel global
    direccion = models.CharField(max_length=255, blank=True, null=True)

    # Asumiendo que 'empresas.Empresa' es la forma correcta de referenciar la FK
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='usuarios')

    objects = CustomUserManager()  # Asigna tu manager personalizado

    # Define el campo a usar como identificador de inicio de sesión
    USERNAME_FIELD = 'username'  # AbstractUser usa 'username' por defecto. Si quieres usar email, cámbialo a 'email'.
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name',
                       'ci']  # Campos que se piden al crear un superusuario (además de USERNAME_FIELD y password)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username if self.username else self.email

    # Método para verificar permisos basados en el code_name del permiso
    def has_permission_code(self, permission_code):
        if self.is_superuser:  # Superusuario siempre tiene todos los permisos
            return True

        # Si el usuario tiene un rol asignado y el rol está activo
        if self.role and self.role.is_active:

            return self.role.permissions.filter(code_name=permission_code, is_active=True).exists()
        return False

