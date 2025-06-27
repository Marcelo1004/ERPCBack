# apps/empresas/urls.py

from django.urls import path
from .views import MarketplaceEmpresaListView, MarketplaceEmpresaDetailView
from apps.productos.views import ProductoListView  # Para la ruta de productos por empresa

urlpatterns = [
    # URLs para el Marketplace de Empresas
    path('marketplace/empresas/', MarketplaceEmpresaListView.as_view(), name='marketplace-empresas-list'),
    path('marketplace/empresas/<int:pk>/', MarketplaceEmpresaDetailView.as_view(), name='marketplace-empresas-detail'),

    # Ruta para productos de una empresa específica en el marketplace
    path('marketplace/empresas/<int:empresa_id>/productos/', ProductoListView.as_view(),
         name='marketplace-productos-by-empresa'),
]