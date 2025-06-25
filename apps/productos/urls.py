from django.urls import path
from .views import ProductoListView, ProductoDetailView # Importa las vistas que definimos

urlpatterns = [
    # Ruta para listar todos los productos y crear uno nuevo
    # Endpoint: /api/productos/
    path('', ProductoListView.as_view(), name='producto_list_create'),

    # Ruta para obtener, actualizar o eliminar un producto específico por ID
    # Endpoint: /api/productos/<int:pk>/
    path('<int:pk>/', ProductoDetailView.as_view(), name='producto_detail_update_delete'),
]

