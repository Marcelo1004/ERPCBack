from django.urls import path
from .views import SucursalListView, SucursalDetailView # Importa las vistas que definimos para sucursales

urlpatterns = [
    path('', SucursalListView.as_view(), name='sucursal_list_create'),

    path('<int:pk>/', SucursalDetailView.as_view(), name='sucursal_detail_update_delete'),
]
