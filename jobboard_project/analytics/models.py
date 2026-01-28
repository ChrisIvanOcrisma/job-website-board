from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job
from applications.models import Application

User = get_user_model()

class JobView(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='job_views')
    viewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['job', 'viewed_at']),
        ]
    
    def __str__(self):
        return f"{self.job.title} viewed at {self.viewed_at}"

class ApplicationEvent(models.Model):
    EVENT_CHOICES = [
        ('APPLIED', 'Applied'),
        ('VIEWED', 'Viewed'),
        ('SHORTLISTED', 'Shortlisted'),
        ('REJECTED', 'Rejected'),
        ('HIRED', 'Hired'),
    ]
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event_type} for {self.application}"