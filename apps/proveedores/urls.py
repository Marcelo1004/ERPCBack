# apps/compras_proveedores/urls.py

from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet

router = DefaultRouter()
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')

urlpatterns = router.urls

# No añadimos las URLs de Compra aún.