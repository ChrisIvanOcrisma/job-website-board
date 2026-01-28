from django.urls import path
from . import views
from .rss_feeds import LatestJobsFeed

urlpatterns = [
    # Job Listings
    path('', views.JobListView.as_view(), name='job_list'),
    path('create/', views.JobCreateView.as_view(), name='job_create'),
    path('<int:pk>/edit/', views.JobUpdateView.as_view(), name='job_update'),
    
    # Job Alerts - MUST BE BEFORE job_detail!
    path('alerts/', views.JobAlertsView.as_view(), name='job_alerts'),
    path('alerts/create/', views.CreateJobAlertView.as_view(), name='create_job_alert'),
    path('alerts/<int:alert_id>/edit/', views.EditJobAlertView.as_view(), name='edit_job_alert'),
    path('alerts/<int:alert_id>/delete/', views.DeleteJobAlertView.as_view(), name='delete_job_alert'),
    path('alerts/<int:alert_id>/preview/', views.PreviewJobAlertView.as_view(), name='preview_job_alert'),
    
    # Saved Jobs
    path('saved/', views.SavedJobsView.as_view(), name='saved_jobs'),
    path('save/<int:job_id>/', views.SaveJobView.as_view(), name='save_job'),
    path('saved/clear/', views.ClearSavedJobsView.as_view(), name='clear_saved_jobs'),
    
    # Job Detail - MUST BE AFTER alerts!
    path('<slug:slug>/', views.JobDetailView.as_view(), name='job_detail'),
    
    # Additional Job Features
    path('search/', views.JobSearchView.as_view(), name='job_search'),
    path('recommended/', views.RecommendedJobsView.as_view(), name='recommended_jobs'),
    path('applications/', views.MyApplicationsView.as_view(), name='my_applications'),
    path('dashboard/', views.JobDashboardView.as_view(), name='job_dashboard'),
    
    # RSS Feed
    path('feed/rss/', LatestJobsFeed(), name='job_feed'),
]