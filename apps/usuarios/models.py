# apps/usuarios/models.py
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from apps.empresas.models import Empresa # Importa el modelo Empresa


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('El campo Email debe ser establecido')
        if not username:
            raise ValueError('El campo Username debe ser establecido')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'SUPERUSER') # Asegura que el rol sea SUPERUSER

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('CLIENTE', 'Cliente'),
        ('SUPERUSER', 'Super_Usuario'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('EMPLEADO', 'Empleado'),
    ]
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CLIENTE'
    )

    telefono = models.CharField(max_length=15, blank=True, null=True)
    ci = models.CharField(max_length=20, unique=True, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='usuarios')

    objects = CustomUserManager()

    # ¡¡¡CAMBIADO AQUÍ!!! Ahora usa 'username' como campo de login
    USERNAME_FIELD = 'username'
    # 'email' ahora es un campo requerido al crear un superusuario, pero no es el campo de login principal
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'ci']

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        # Este bloque debe seguir COMENTADO o ELIMINADO si ya no se requiere esta validación estricta
        # if not self.is_superuser and not self.empresa:
        #     raise ValidationError("Un usuario que no es Super_Usuario debe estar asignado a una empresa.")

    def save(self, *args, **kwargs):
        # self.clean() # Mantener si tienes otras validaciones en clean()
        super().save(*args, **kwargs)

    @property
    def is_client(self):
        return self.role == 'CLIENTE'

    @property
    def is_admin_or_employee(self):
        return self.role in ['ADMINISTRATIVO', 'EMPLEADO']