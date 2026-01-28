from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from users.views import RegisterView, CustomLoginView
from users.views import DashboardView 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    # Home
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    
path('users/', include('users.urls')),
    
    # Companies
    path('companies/', include('companies.urls')),
    
    # Jobs
    path('jobs/', include('jobs.urls')),
    
    # Applications
    path('applications/', include('applications.urls')),
    
    # RSS Feed
    path('rss/', include('jobs.rss_urls')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)