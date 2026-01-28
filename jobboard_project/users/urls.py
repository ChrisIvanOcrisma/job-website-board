# users/urls.py - UPDATE:
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),  # CHANGE TO YOUR VIEW
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
]