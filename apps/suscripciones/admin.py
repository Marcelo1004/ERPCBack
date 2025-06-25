from django.contrib import admin
from .models import Suscripcion

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    """
    Configuración para la visualización del modelo Suscripcion en el panel de administración.
    """
    list_display = ('nombre', 'cantidad_usuarios_permitidos', 'descripcion')
    search_fields = ('nombre', 'descripcion')
    list_filter = ('cantidad_usuarios_permitidos',)

