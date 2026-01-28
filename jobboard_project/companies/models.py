from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class Company(models.Model):
    # DITO LAGAY ANG INDUSTRY CHOICES
    INDUSTRY_CHOICES = [
        ('Technology', 'Technology'),
        ('Healthcare', 'Healthcare'),
        ('Finance', 'Finance'),
        ('Education', 'Education'),
        ('Retail', 'Retail'),
        ('Manufacturing', 'Manufacturing'),
        ('Hospitality', 'Hospitality'),
        ('Construction', 'Construction'),
        ('Transportation', 'Transportation'),
        ('Real Estate', 'Real Estate'),
        ('Media & Entertainment', 'Media & Entertainment'),
        ('Energy', 'Energy'),
        ('Telecommunications', 'Telecommunications'),
        ('Government', 'Government'),
        ('Non-Profit', 'Non-Profit'),
        ('Other', 'Other'),
    ]
    
    employer = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'EMPLOYER'})
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    description = models.TextField()
    website = models.URLField(blank=True)
    location = models.CharField(max_length=200)
    address = models.TextField()
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    # PALITAN ANG INDUSTRY FIELD - GAMITIN ANG CHOICES!
    industry = models.CharField(
        max_length=100, 
        choices=INDUSTRY_CHOICES,
        blank=True,  # Pwede gawing False kung required
        verbose_name="Industry/Sector",
        help_text="Select your company's primary industry"
    )
    
    size = models.CharField(max_length=50, blank=True)
    founded_year = models.IntegerField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('company_detail', kwargs={'slug': self.slug})
    
    # OPTIONAL: Add a method to get active jobs count
    def active_jobs_count(self):
        return self.jobs.filter(is_active=True).count()