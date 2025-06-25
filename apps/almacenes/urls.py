from django.urls import path
from .views import AlmacenListView, AlmacenDetailView # Importa las vistas que definimos

urlpatterns = [
    # Ruta para listar todos los almacenes y crear uno nuevo
    # Endpoint: /api/almacenes/
    path('', AlmacenListView.as_view(), name='almacen_list_create'),

    # Ruta para obtener, actualizar o eliminar un almacén específico por ID
    # Endpoint: /api/almacenes/<int:pk>/
    path('<int:pk>/', AlmacenDetailView.as_view(), name='almacen_detail_update_delete'),
]
