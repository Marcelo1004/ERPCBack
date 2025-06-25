from django.urls import path
from .views import EmpresaListView, EmpresaDetailView

urlpatterns = [
    # Rutas para listar todas las empresas y crear una nueva (solo SuperUser)
    # Endpoint: /api/empresas/
    path('', EmpresaListView.as_view(), name='empresa_list_create'),

    # Rutas para obtener, actualizar o eliminar una empresa específica por ID
    # Endpoint: /api/empresas/<int:pk>/
    path('<int:pk>/', EmpresaDetailView.as_view(), name='empresa_detail_update_delete'),
]

