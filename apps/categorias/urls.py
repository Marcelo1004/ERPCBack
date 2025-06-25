from django.urls import path
from .views import CategoriaListView, CategoriaDetailView # Importa las vistas que definimos para sucursales

urlpatterns = [
    path('', CategoriaListView.as_view(), name='categoria_list_create'),

    path('<int:pk>/', CategoriaDetailView.as_view(), name='categoria_detail_update_delete'),
]
