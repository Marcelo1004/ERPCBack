from django.contrib import admin
from .models import Categoria

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """
    Configuración para la visualización del modelo Categoria en el panel de administración.
    """
    list_display = ('nombre', 'descripcion', 'empresa') # Añade 'empresa' para ver a qué empresa pertenece
    search_fields = ('nombre', 'descripcion', 'empresa__nombre') # Permite buscar por nombre de empresa
    list_filter = ('empresa',)