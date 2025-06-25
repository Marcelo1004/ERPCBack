from django.contrib import admin
from .models import Sucursal

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    """
    Configuración para la visualización del modelo Sucursal en el panel de administración.
    """
    list_display = ('nombre', 'direccion', 'telefono')
    search_fields = ('nombre', 'direccion', 'telefono')
    list_filter = ('nombre',) # Puedes añadir más filtros si es necesari