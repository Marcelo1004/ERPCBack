# tu_proyecto/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# --- Importar el DefaultRouter UNA SOLA VEZ ---
from rest_framework.routers import DefaultRouter

# --- Importar TODOS tus ViewSets ---
# Asegúrate de que las rutas de importación sean correctas para cada app
from apps.rbac.views import PermissionViewSet, RoleViewSet
from apps.usuarios.views import UserViewSet
from apps.sucursales.views import SucursalViewSet
from apps.almacenes.views import AlmacenViewSet
from apps.categorias.views import CategoriaViewSet
from apps.empresas.views import EmpresaViewSet
from apps.logs.views import ActividadLogViewSet
from apps.ventas.views import VentaViewSet, DetalleVentaViewSet
from apps.proveedores.views import ProveedorViewSet
from apps.suscripciones.views import SuscripcionViewSet
from apps.productos.views import ProductoViewSet
from apps.movimientos.views import MovimientoViewSet


# --- Inicializar el ÚNICO router ---
router = DefaultRouter()

# --- Registrar TODOS tus ViewSets aquí ---
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', UserViewSet, basename='user') # <-- Registrado en el router principal
router.register(r'sucursales', SucursalViewSet, basename='sucursal')
router.register(r'almacenes', AlmacenViewSet, basename='almacen')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'logs', ActividadLogViewSet, basename='log')
router.register(r'ventas', VentaViewSet, basename='venta')
router.register(r'detalles-venta', DetalleVentaViewSet, basename='detalle_venta')
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'suscripciones', SuscripcionViewSet, basename='suscripcion')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'movimientos', MovimientoViewSet, basename='movimiento')


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

    # --- Incluir TODAS las URLs generadas por el router bajo el prefijo 'api/' ---
    path('api/', include(router.urls)), # Maneja todas las rutas de tus ViewSets (incluyendo /api/users/)

    # --- Las URLs de 'apps.usuarios' que son manuales (login, registro, perfil) ---
    path('api/usuarios/', include('apps.usuarios.urls')), # <-- Esta sigue incluyendo las rutas manuales de la app usuarios.

    path('api/dashboard/', include('apps.dashboard.urls')),

    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)