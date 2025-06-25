from django.contrib import admin
from .models import Almacen

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    """
    Configuración para la visualización del modelo Almacen en el panel de administración.
    """
    list_display = ('nombre', 'sucursal', 'ubicacion', 'capacidad')
    search_fields = ('nombre', 'ubicacion', 'sucursal__nombre') # Permite buscar por nombre de sucursal
    list_filter = ('sucursal',) # Filtrar por sucursal

