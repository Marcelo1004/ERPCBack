from django.urls import path
from .views import SuscripcionListView, SuscripcionDetailView

urlpatterns = [
    path('', SuscripcionListView.as_view(), name='suscripcion_list_create'),
    path('<int:pk>/', SuscripcionDetailView.as_view(), name='suscripcion_detail_update_delete'),
]

