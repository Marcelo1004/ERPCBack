# apps/empresas/admin.py
from django.contrib import admin
from .models import Empresa

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """
    Configuración para la visualización del modelo Empresa en el panel de administración.
    """
    list_display = ('nombre', 'nit', 'telefono', 'suscripcion', 'admin_empresa', 'is_active', 'fecha_registro')
    search_fields = ('nombre', 'nit', 'email_contacto')
    list_filter = ('suscripcion', 'is_active', 'fecha_registro')
    raw_id_fields = ('suscripcion', 'admin_empresa') # Usar un widget de búsqueda para FKs a muchos objetos

