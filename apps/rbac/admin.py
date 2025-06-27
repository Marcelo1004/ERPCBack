# apps/rbac/admin.py

from django.contrib import admin
from .models import Permission, Role

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code_name', 'is_active', 'fecha_creacion')
    list_filter = ('is_active',)
    search_fields = ('name', 'code_name', 'description')
    ordering = ('name',)

    # Restringe el acceso a este modelo solo a superusuarios
    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'fecha_creacion')
    list_filter = ('is_active', 'permissions')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',) # Interfaz más amigable para ManyToManyField
    ordering = ('name',)

    # Restringe el acceso a este modelo solo a superusuarios
    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser