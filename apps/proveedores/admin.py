# apps/compras_proveedores/admin.py

from django.contrib import admin
from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'contacto_email', 'contacto_telefono', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('nombre', 'contacto_nombre', 'contacto_email', 'nit')
    ordering = ('nombre',)

    # Permite al admin filtrar proveedores por su empresa si no es superuser
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()

    # Pre-llenar la empresa para nuevos proveedores si el usuario no es superuser
    def save_model(self, request, obj, form, change):
        if not obj.pk and not request.user.is_superuser and request.user.empresa:
            obj.empresa = request.user.empresa
        super().save_model(request, obj, form, change)

    # Asegurarse de que el campo empresa esté deshabilitado si no es superuser
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and 'empresa' in form.base_fields:
            form.base_fields['empresa'].disabled = True
        return form

# No registramos los modelos de Compra/DetalleCompra aún.