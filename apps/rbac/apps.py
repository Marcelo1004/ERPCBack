# apps/rbac/apps.py

from django.apps import AppConfig

class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rbac'
    verbose_name = 'Control de Acceso Basado en Roles (RBAC)'

    def ready(self):
        # Importar señales aquí para asegurar que los modelos estén cargados
        # y que el manejador de señales se registre.
        import apps.rbac.signals