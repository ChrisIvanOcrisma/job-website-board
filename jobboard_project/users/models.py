from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        EMPLOYER = 'EMPLOYER', _('Employer')
        JOB_SEEKER = 'JOB_SEEKER', _('Job Seeker')
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.JOB_SEEKER
    )
    
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    def is_employer(self):
        return self.role == self.Role.EMPLOYER
    
    def is_job_seeker(self):
        return self.role == self.Role.JOB_SEEKER