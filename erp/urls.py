from django.contrib import admin
from django.urls import path, include,re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="ERP Cloud Solutions API",
        default_version='v1',
        description="Documentación de la API para el sistema de Gestión ERP Cloud.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contacto@tuempresa.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/usuarios/', include('apps.usuarios.urls')),
    path('api/sucursales/', include('apps.sucursales.urls')),
    path('api/almacenes/', include('apps.almacenes.urls')),
    path('api/categorias/', include('apps.categorias.urls')),
    path('api/productos/', include('apps.productos.urls')),
    path('api/suscripciones/', include('apps.suscripciones.urls')),
    path('api/empresas/', include('apps.empresas.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/ventas/', include('apps.ventas.urls')),
    path('api/logs/', include('apps.logs.urls')),
    path('api/', include('apps.proveedores.urls')),



]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

