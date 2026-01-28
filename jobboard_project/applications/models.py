from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job, ScreeningQuestion
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()

class Application(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('REVIEWED', 'Reviewed'),
        ('SHORTLISTED', 'Shortlisted'),
        ('INTERVIEW', 'Interview Scheduled'),
        ('OFFER', 'Offer Extended'),
        ('HIRED', 'Hired'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),  # MERON NA ITO
    ]
    
    EDUCATION_LEVELS = [
        ('HIGH_SCHOOL', 'High School'),
        ('ASSOCIATE', 'Associate Degree'),
        ('BACHELOR', 'Bachelor\'s Degree'),
        ('MASTER', 'Master\'s Degree'),
        ('DOCTORATE', 'Doctorate'),
        ('VOCATIONAL', 'Vocational/Trade School'),
        ('OTHER', 'Other'),
    ]
    
    NOTICE_PERIODS = [
        ('IMMEDIATE', 'Immediate'),
        ('15_DAYS', '15 days'),
        ('30_DAYS', '30 days'),
        ('60_DAYS', '60 days'),
        ('90_DAYS', '90 days'),
        ('CUSTOM', 'Custom'),
    ]
    
    # JOB & APPLICANT
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    
    # PERSONAL INFORMATION - ADDED DEFAULT VALUES
    full_name = models.CharField(max_length=200, default='Not provided')
    email = models.EmailField(default='notprovided@example.com')
    phone = models.CharField(max_length=20, default='Not provided')
    location = models.CharField(max_length=100, default='Not specified')
    linkedin_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    
    # PROFESSIONAL BACKGROUND - ADDED DEFAULT VALUES
    current_position = models.CharField(max_length=200, default='Not specified')
    years_experience = models.CharField(max_length=50, default='Not specified')
    skills = models.TextField(default='Not specified', help_text="Comma-separated list of skills")
    expected_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    notice_period = models.CharField(
        max_length=20, 
        choices=NOTICE_PERIODS, 
        default='30_DAYS'
    )
    custom_notice = models.CharField(max_length=100, blank=True, null=True)
    available_start_date = models.DateField(null=True, blank=True)
    
    # EDUCATION BACKGROUND - ADDED DEFAULT VALUES
    education_level = models.CharField(
        max_length=20, 
        choices=EDUCATION_LEVELS, 
        default='BACHELOR'
    )
    degree = models.CharField(max_length=200, default='Not specified')
    university = models.CharField(max_length=200, default='Not specified')
    graduation_year = models.IntegerField(
        default=2024,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    
    # DOCUMENTS
    resume = models.FileField(upload_to='applications/resumes/%Y/%m/%d/')
    cover_letter = models.TextField()
    additional_docs = models.FileField(
        upload_to='applications/additional/%Y/%m/%d/',
        blank=True,
        null=True
    )
    
    # APPLICATION STATUS
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    status_notes = models.TextField(blank=True, null=True)
    
    # WITHDRAWAL FIELDS - DAGDAG MO ITO
    withdraw_reason = models.TextField(blank=True, null=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    
    # REFERRAL TRACKING
    referred_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='referrals'
    )
    referral_source = models.CharField(max_length=200, blank=True, null=True)
    
    # RATING & NOTES (for employer use)
    rating = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="1-5 rating from employer"
    )
    employer_notes = models.TextField(blank=True, null=True)
    
    # TIMESTAMPS
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['job', 'applicant']
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['status', 'applied_at']),
            models.Index(fields=['job', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-fill user information and track status changes"""
        # Track status change
        status_changed = False
        old_status = None
        
        if self.pk:
            try:
                original = Application.objects.get(pk=self.pk)
                old_status = original.status
                if old_status != self.status:
                    status_changed = True
            except Application.DoesNotExist:
                pass
        
        # Auto-fill user information
        if not self.full_name or self.full_name == 'Not provided':
            self.full_name = self.applicant.get_full_name() or self.applicant.username
        
        if not self.email or self.email == 'notprovided@example.com':
            self.email = self.applicant.email
        
        # Check if user has a profile with additional info
        if hasattr(self.applicant, 'profile'):
            profile = self.applicant.profile
            
            if not self.phone or self.phone == 'Not provided':
                self.phone = getattr(profile, 'phone', 'Not provided')
            
            if not self.location or self.location == 'Not specified':
                self.location = getattr(profile, 'location', 'Not specified')
            
            if not self.current_position or self.current_position == 'Not specified':
                self.current_position = getattr(profile, 'current_position', 'Not specified')
            
            if hasattr(profile, 'skills') and profile.skills:
                if not self.skills or self.skills == 'Not specified':
                    self.skills = profile.skills
        
        # Save the application
        super().save(*args, **kwargs)
        
        # Create status history after save (so we have access to the application instance)
        if status_changed and old_status:
            ApplicationStatusHistory.objects.create(
                application=self,
                old_status=old_status,
                new_status=self.status,
                changed_by=self.job.company.employer if hasattr(self.job, 'company') and hasattr(self.job.company, 'employer') else None,
                notes=f"Status changed from {old_status} to {self.status}"
            )
            
            # Send email notification when status changes
            try:
                from applications.emails import send_application_status_email
                send_application_status_email(self, old_status)
            except Exception as e:
                print(f"Email sending failed: {e}")
                # Continue even if email fails
    
    def update_status(self, new_status, changed_by=None, notes=None, send_email=True):
        """Helper method to update status and create history"""
        old_status = self.status
        self.status = new_status
        
        # Set withdrawn timestamp if withdrawing
        if new_status == 'WITHDRAWN' and old_status != 'WITHDRAWN':
            self.withdrawn_at = timezone.now()
            
        self.save()
        
        # Create detailed history record
        if old_status != new_status:
            ApplicationStatusHistory.objects.create(
                application=self,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                notes=notes or f"Status changed from {old_status} to {new_status}"
            )
            
            # Send email notification
            if send_email:
                try:
                    from applications.emails import send_application_status_email
                    send_application_status_email(self, old_status)
                except Exception as e:
                    print(f"Email sending failed: {e}")
    
    # DAGDAG NG FUNCTION PARA SA WITHDRAWAL
    def withdraw(self, reason=None, changed_by=None, send_email=True):
        """Withdraw application"""
        if self.status == 'WITHDRAWN':
            return False, "Application already withdrawn"
            
        if self.status in ['HIRED', 'REJECTED']:
            return False, "Cannot withdraw application with current status"
        
        self.withdraw_reason = reason
        self.update_status('WITHDRAWN', changed_by, 
                          f"Application withdrawn. Reason: {reason or 'Not specified'}",
                          send_email=send_email)
        
        return True, "Application withdrawn successfully"
    
    def __str__(self):
        return f"{self.full_name} - {self.job.title} ({self.status})"
    
    def get_skills_list(self):
        """Return skills as a list"""
        return [skill.strip() for skill in self.skills.split(',') if skill.strip()]
    
    def get_formatted_salary(self):
        """Return formatted salary with currency"""
        if self.expected_salary and self.job.salary_currency:
            return f"{self.job.salary_currency} {self.expected_salary:,.2f}"
        elif self.expected_salary:
            return f"₱ {self.expected_salary:,.2f}"
        return "Negotiable"
    
    @property
    def is_active(self):
        """Check if application is still active"""
        return self.status not in ['REJECTED', 'WITHDRAWN', 'HIRED']
    
    @property
    def can_withdraw(self):
        """Check if application can be withdrawn"""
        return self.status not in ['WITHDRAWN', 'HIRED', 'REJECTED']
    
    @property
    def applicant_info(self):
        """Get applicant info for display"""
        return {
            'name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
        }
    
    @property
    def status_color(self):
        """Return Bootstrap color class for status"""
        colors = {
            'PENDING': 'secondary',
            'REVIEWED': 'info',
            'SHORTLISTED': 'warning',
            'INTERVIEW': 'primary',
            'OFFER': 'success',
            'HIRED': 'success',
            'REJECTED': 'danger',
            'WITHDRAWN': 'dark',
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def status_icon(self):
        """Return icon for status"""
        icons = {
            'PENDING': 'bi-clock',
            'REVIEWED': 'bi-eye',
            'SHORTLISTED': 'bi-star',
            'INTERVIEW': 'bi-calendar-event',
            'OFFER': 'bi-award',
            'HIRED': 'bi-check-circle',
            'REJECTED': 'bi-x-circle',
            'WITHDRAWN': 'bi-arrow-left',
        }
        return icons.get(self.status, 'bi-clock')

class ScreeningResponse(models.Model):
    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name='screening_responses'
    )
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
    
    class Meta:
        unique_together = ['application', 'question']
        verbose_name = 'Screening Response'
        verbose_name_plural = 'Screening Responses'
    
    def __str__(self):
        return f"Response: {self.question.question[:50]}..."

class ApplicationNote(models.Model):
    """Additional notes/comments on applications (for employers)"""
    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name='notes'
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note by {self.author.username} on {self.application}"

class ApplicationStatusHistory(models.Model):
    """Track status changes of applications"""
    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Application Status History'
    
    def __str__(self):
        return f"{self.application} : {self.old_status} → {self.new_status}"
    
    @property
    def event_type(self):
        """Convert status change to event type for display"""
        if self.new_status == 'PENDING':
            return 'APPLIED'
        elif self.new_status == 'REVIEWED':
            return 'REVIEWED'
        elif self.new_status == 'SHORTLISTED':
            return 'SHORTLISTED'
        elif self.new_status == 'INTERVIEW':
            return 'INTERVIEW'
        elif self.new_status == 'OFFER':
            return 'OFFER'
        elif self.new_status == 'HIRED':
            return 'HIRED'
        elif self.new_status == 'REJECTED':
            return 'REJECTED'
        elif self.new_status == 'WITHDRAWN':
            return 'WITHDRAWN'
        return 'STATUS_CHANGE'
    
 # applications/models.py - add this after ApplicationStatusHistory
class Interview(models.Model):
    """Simplified interview scheduling - date, time, location only"""
    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name='interviews'
    )
    
    # Basic fields only
    interview_date = models.DateField()
    interview_time = models.TimeField()
    location = models.CharField(max_length=500)
    
    # Timestamps
    scheduled_at = models.DateTimeField(auto_now_add=True)
    scheduled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='scheduled_interviews'
    )
    
    class Meta:
        ordering = ['interview_date', 'interview_time']
    
    def __str__(self):
        return f"Interview: {self.application.full_name} - {self.interview_date}"
    
    @property
    def full_datetime(self):
        """Return combined datetime"""
        import datetime
        return datetime.datetime.combine(self.interview_date, self.interview_time)
    
    @property
    def is_upcoming(self):
        """Check if interview is upcoming"""
        from django.utils import timezone
        return self.full_datetime > timezone.now()