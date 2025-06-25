from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    RegisterView,
    UserProfileView,
    UserListView,
    AdminUserDetailUpdateDeleteView, # Esta vista combina GET, PUT, DELETE para usuarios por admin
)
urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('registro/', RegisterView.as_view(), name='user_register'),
    path('perfil/', UserProfileView.as_view(), name='user_profile'),
    path('admin/lista/', UserListView.as_view(), name='admin_user_list'),
    path('admin/<int:user_id>/', AdminUserDetailUpdateDeleteView.as_view(), name='admin_user_detail_update_delete'),
]
