from django.urls import path
from . import views

urlpatterns = [
    path('', views.CompanyListView.as_view(), name='company_list'),
    path('create/', views.CompanyCreateView.as_view(), name='company_create'),
    path('update/', views.CompanyUpdateView.as_view(), name='company_update'),
    path('<slug:slug>/', views.CompanyDetailView.as_view(), name='company_detail'),
]