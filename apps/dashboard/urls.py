from django.urls import path
from .views import DashboardERPView # ¡Importación corregida!

urlpatterns = [
    # Ruta para el Dashboard General/por Empresa
    # Endpoint: /api/dashboard/
    path('', DashboardERPView.as_view(), name='erp_dashboard'),
]