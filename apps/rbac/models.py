from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

class Permission(models.Model):

    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Permiso")
    code_name = models.CharField(max_length=100, unique=True, verbose_name="Código del Permiso")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"
        ordering = ['name']

    def __str__(self):
        return self.name

class Role(models.Model):

    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Rol")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    # Los permisos se relacionan con un ManyToManyField
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles', verbose_name="Permisos")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name