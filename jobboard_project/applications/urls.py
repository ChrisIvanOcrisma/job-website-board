from django.urls import path
from . import views

urlpatterns = [
    # APPLICATION WITHDRAW
    path('<int:pk>/withdraw/', views.ApplicationWithdrawView.as_view(), name='application_withdraw'),
    path('api/<int:pk>/withdraw/', views.withdraw_application_api, name='withdraw_application_api'),
    path('<int:pk>/reactivate/', views.ApplicationReactivateView.as_view(), name='application_reactivate'),
    
    # GENERAL APPLICATION LIST (for dashboard)
    path('', views.ApplicationListView.as_view(), name='application_list'),
    
    # APPLICATIONS FOR SPECIFIC JOB
    path('job/<int:job_id>/', views.ApplicationListView.as_view(), name='application_list_by_job'),
    
    # APPLICATION CREATE (for specific job)
    path('job/<int:job_id>/create/', views.ApplicationCreateView.as_view(), name='application_create'),
    
    # APPLICATION DETAIL/UPDATE/DELETE/STATUS
    path('<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('<int:pk>/update/', views.ApplicationUpdateView.as_view(), name='application_update'),
    path('<int:pk>/delete/', views.ApplicationDeleteView.as_view(), name='application_delete'),
    
    # UPDATED: Status update (now includes interview) - PALITAN ANG PANGALAN!
    path('<int:pk>/update-status/', views.ApplicationStatusUpdateView.as_view(), name='application_status'),
       path('<int:pk>/status/', views.ApplicationStatusUpdateView.as_view(), name='application_status'),
    
    # OPTIONAL: Separate interview scheduling (kung gusto mo pa rin)
    # path('<int:pk>/schedule-interview/', views.ScheduleInterviewSimpleView.as_view(), name='schedule_interview_simple'),
    
    # ============ EXPORT FUNCTIONS ============
    # Export all applications
    path('export/csv/', views.export_applications_csv, name='export_applications_csv'),
    path('export/excel/', views.export_applications_excel, name='export_applications_excel'),
    
    # Export applications for specific job
    path('job/<slug:job_slug>/export/csv/', views.export_applications_csv, name='export_job_applications_csv'),
    path('job/<slug:job_slug>/export/excel/', views.export_applications_excel, name='export_job_applications_excel'),
    
    # ============ BULK ACTIONS ============
    path('bulk-update/', views.bulk_update_applications, name='bulk_update_applications'),
]