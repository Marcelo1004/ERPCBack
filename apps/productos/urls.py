# apps/productos/urls.py
from django.urls import path
from .views import ProductoListView, ProductoDetailView, DemandaPredictivaView

urlpatterns = [
    # Esta ruta ahora será: /api/public-products/empresas/<int:empresa_id>/productos/
    # (¡Atención! Este es un prefijo doble si el objetivo es solo 'productos de una empresa pública')
    # Podríamos simplificarla a solo 'empresas/<int:empresa_id>/productos/' si esa es la intención.
    # Pero si el frontend apunta a /api/productos/empresas/<id>/productos, entonces está bien.
    # Para la coherencia del marketplace:
    # URL para ver productos DE UNA EMPRESA EN ESPECÍFICO dentro del Marketplace
    # Se accederá como: /api/marketplace/empresas/<id>/productos/
    # Esto significa que esta URL NO debería estar bajo /api/public-products/
    # ¡Esta ruta DEBE MOVERSE a apps/empresas/urls.py o ser una vista con ruta separada!
    # Dejémosla aquí por ahora para no complicar, pero ten en cuenta la duplicidad del prefijo "productos" en la URL final.
    # La URL final para esto sería: /api/public-products/empresas/<int:empresa_id>/productos/
    # Esto es muy largo.
    #
    # === MEJOR CAMBIO ===
    # El `ProductoListView` que lista productos de una empresa en particular (para la tienda)
    # DEBERÍA estar en `apps/empresas/urls.py` si su URL empieza con `/marketplace/empresas/<id>/productos/`.
    # O bien, si es una vista "general" de productos, su URL debería ser más simple.

    # Propuesta:
    # 1. Mover ProductoListView (para productos de una empresa) a apps/empresas/urls.py
    # 2. Dejar ProductoDetailView y DemandaPredictivaView bajo el prefijo /api/public-products/


    # Opción 1: Manteniendo ProductoListView aquí, pero ajustando la URL esperada
    # Esta ruta se accederá como: /api/public-products/por-empresa/<int:empresa_id>/
    # (El frontend deberá cambiar la llamada)
    path('por-empresa/<int:empresa_id>/', ProductoListView.as_view(), name='producto-list-by-empresa'),


    # Estas rutas se accederán como: /api/public-products/<int:pk>/ y /api/public-products/<int:pk>/demanda-predictiva/
    path('<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
    path('<int:pk>/demanda-predictiva/', DemandaPredictivaView.as_view(), name='producto-demanda-predictiva'),
]