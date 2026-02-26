from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import api_views, views

urlpatterns = [
    path('login/', views.PainelLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('welcome/', views.welcome_view, name='welcome'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/status/', views.api_status, name='api_status'),
    path('api/me', views.api_me, name='api_me'),
    path('api/users/', api_views.UserListCreateView.as_view(), name='users_list_create'),
    path('api/users/<int:pk>/', api_views.UserDetailView.as_view(), name='users_detail'),
    path('api/groups/', api_views.GroupListCreateView.as_view(), name='groups_list_create'),
    path('api/groups/<int:pk>/', api_views.GroupDetailView.as_view(), name='groups_detail'),
    path(
        'api/users/<int:pk>/reset-password/',
        api_views.ResetPasswordView.as_view(),
        name='users_reset_password',
    ),
    path(
        'api/users/me/change-password/',
        api_views.ChangeOwnPasswordView.as_view(),
        name='users_change_password',
    ),
]
