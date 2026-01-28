from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Q
from .models import JobAlert, Job
from datetime import datetime, timedelta

@shared_task
def send_job_alerts():
    """
    Send weekly job alerts to subscribers
    """
    alerts = JobAlert.objects.filter(
        is_active=True,
        email_notifications=True
    )
    
    for alert in alerts:
        # Find new jobs matching the alert criteria
        new_jobs = Job.objects.filter(
            is_active=True,
            created_at__gte=datetime.now() - timedelta(days=7)
        )
        
        if alert.keyword:
            new_jobs = new_jobs.filter(
                Q(title__icontains=alert.keyword) |
                Q(description__icontains=alert.keyword)
            )
        
        if alert.location:
            new_jobs = new_jobs.filter(location__icontains=alert.location)
        
        if alert.category:
            new_jobs = new_jobs.filter(category=alert.category)
        
        if alert.is_remote:
            new_jobs = new_jobs.filter(is_remote=True)
        
        if new_jobs.exists():
            # Send email
            context = {
                'user': alert.job_seeker,
                'jobs': new_jobs[:10],  # Limit to 10 jobs
                'alert': alert,
            }
            
            html_message = render_to_string('emails/job_alert.html', context)
            plain_message = render_to_string('emails/job_alert.txt', context)
            
            send_mail(
                subject=f'New Jobs Matching Your Alert - {datetime.now().strftime("%Y-%m-%d")}',
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert.job_seeker.email],
                fail_silently=True,
            )
            
            # Update last_sent timestamp
            alert.last_sent = datetime.now()
            alert.save(update_fields=['last_sent'])
    
    return f"Sent alerts to {alerts.count()} subscribers"