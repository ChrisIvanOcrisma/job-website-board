from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from companies.models import Company
from django.utils import timezone
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.apps import apps

User = get_user_model()

class JobCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Job Categories"
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class JobTag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Job(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERNSHIP', 'Internship'),
        ('REMOTE', 'Remote'),
    ]
    
    EDUCATION_CHOICES = [
        ('HIGH_SCHOOL', 'High School Diploma'),
        ('VOCATIONAL', 'Vocational/TESDA'),
        ('ASSOCIATE', 'Associate Degree'),
        ('BACHELOR', "Bachelor's Degree"),
        ('MASTER', "Master's Degree"),
        ('DOCTORATE', 'Doctorate'),
        ('NONE', 'No formal education required'),
    ]
    
    EXPERIENCE_CHOICES = [
        (0, 'No experience (Entry level)'),
        (1, '1-2 years'),
        (3, '3-5 years'),
        (6, '6-10 years'),
        (11, '10+ years'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    
    qualifications = models.TextField(blank=True, verbose_name="Qualifications")
    education_level = models.CharField(
        max_length=20,
        choices=EDUCATION_CHOICES,
        blank=True,
        null=True,
        verbose_name="Minimum Education Required"
    )
    experience_years = models.IntegerField(
        choices=EXPERIENCE_CHOICES,
        default=0,
        verbose_name="Years of Experience Required"
    )
    skills = models.TextField(blank=True, verbose_name="Skills")
    
    benefits = models.TextField(blank=True)
    location = models.CharField(max_length=200)
    is_remote = models.BooleanField(default=False)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(JobTag, blank=True)
    
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='PHP')
    
    application_email = models.EmailField(blank=True)
    application_url = models.URLField(blank=True)
    
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    views = models.PositiveIntegerField(default=0)
    
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['education_level']),
            models.Index(fields=['experience_years']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.company.name}")
            self.slug = base_slug
        
        if self.slug:
            original_slug = self.slug
            counter = 1
            
            while True:
                query = Job.objects.filter(slug=self.slug)
                if self.pk:
                    query = query.exclude(pk=self.pk)
                
                if not query.exists():
                    break
                
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        if not self.published_at and self.is_active:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        if is_new and self.is_active:
            self.check_job_alerts()
    
    def check_job_alerts(self):
        JobAlert = apps.get_model('jobs', 'JobAlert')
        
        alerts = JobAlert.objects.filter(
            frequency='INSTANT',
            email_notifications=True,
            is_active=True
        )
        
        print(f"\n🔍 DEBUG: Checking job alerts for new job: {self.title}")
        print(f"🔍 DEBUG: Total instant alerts found: {alerts.count()}")
        
        email_sent_count = 0
        for alert in alerts:
            print(f"\n🔍 DEBUG: Processing alert '{alert.name}' for {alert.job_seeker.email}")
            
            if alert.does_job_match(self):
                print(f"✅ DEBUG: Job MATCHES alert criteria")
                
                if not alert.last_sent or (timezone.now() - alert.last_sent).seconds > 300:
                    print(f"📧 DEBUG: Sending email notification...")
                    if alert.send_single_job_email(self):
                        email_sent_count += 1
                        print(f"✅ DEBUG: Email sent successfully")
                    else:
                        print(f"❌ DEBUG: Failed to send email")
                else:
                    print(f"⏰ DEBUG: Email already sent recently (within 5 minutes)")
            else:
                print(f"❌ DEBUG: Job does NOT match alert criteria")
        
        print(f"\n📊 DEBUG: Total emails sent for this job: {email_sent_count}")
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('job_detail', kwargs={'slug': self.slug})
    
    def get_salary_range(self):
        if self.salary_min and self.salary_max:
            return f"₱{self.salary_min:,.2f} - ₱{self.salary_max:,.2f}"
        elif self.salary_min:
            return f"From ₱{self.salary_min:,.2f}"
        elif self.salary_max:
            return f"Up to ₱{self.salary_max:,.2f}"
        return "Negotiable"
    
    def get_education_level_display(self):
        for value, label in self.EDUCATION_CHOICES:
            if value == self.education_level:
                return label
        return "Not specified"
    
    def get_experience_display(self):
        for value, label in self.EXPERIENCE_CHOICES:
            if value == self.experience_years:
                return label
        return "Not specified"
    
    def get_employment_type_display(self):
        for value, label in self.EMPLOYMENT_TYPE_CHOICES:
            if value == self.employment_type:
                return label
        return self.employment_type

class ScreeningQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('CHECKBOX', 'Checkbox'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='screening_questions')
    question = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='TEXT')
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.job.title}: {self.question[:50]}"

class QuestionChoice(models.Model):
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=200)
    
    def __str__(self):
        return self.choice_text

class SavedJob(models.Model):
    job_seeker = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'JOB_SEEKER'})
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['job_seeker', 'job']
    
    def __str__(self):
        return f"{self.job_seeker.username} saved {self.job.title}"

class JobAlert(models.Model):
    FREQUENCY_CHOICES = [
        ('INSTANT', 'Instant'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
    ]
    
    job_seeker = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'JOB_SEEKER'})
    name = models.CharField(max_length=200, default="My Job Alert", verbose_name="Alert Name")
    
    keyword = models.CharField(max_length=100, blank=True, help_text="Job title, skills, or company")
    location = models.CharField(max_length=100, blank=True, help_text="City, state, or remote")
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    employment_type = models.CharField(
        max_length=20, 
        choices=Job.EMPLOYMENT_TYPE_CHOICES, 
        blank=True, 
        null=True,
        verbose_name="Job Type"
    )
    
    is_remote = models.BooleanField(null=True, blank=True, verbose_name="Remote Work")
    
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Minimum Salary")
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Maximum Salary")
    
    education_level = models.CharField(
        max_length=20,
        choices=Job.EDUCATION_CHOICES,
        blank=True,
        null=True,
        verbose_name="Education Level"
    )
    
    experience_years = models.IntegerField(
        choices=Job.EXPERIENCE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Experience Level"
    )
    
    frequency = models.CharField(
        max_length=10, 
        choices=FREQUENCY_CHOICES, 
        default='DAILY', 
        verbose_name="Frequency"
    )
    
    email_notifications = models.BooleanField(default=True, verbose_name="Send Email Notifications")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Job Alert'
        verbose_name_plural = 'Job Alerts'
    
    def __str__(self):
        return f"{self.name} - {self.job_seeker.username}"
    
    def does_job_match(self, job):
        """Check if a specific job matches ALL alert criteria - STRICT CHECK"""
        
        # 1. KEYWORD - DAPAT NASA JOB TITLE (kung may keyword sa alert)
        if self.keyword and self.keyword.strip():
            keyword = self.keyword.strip().lower()
            job_title = job.title.lower()
            
            # Keyword dapat nasa job title
            if keyword not in job_title:
                print(f"❌ Keyword '{keyword}' NOT in job title '{job_title}'")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Keyword found in job title")
        
        # 2. LOCATION - DAPAT NASA JOB LOCATION (kung may location sa alert)
        if self.location and self.location.strip():
            location = self.location.strip().lower()
            job_location = job.location.lower()
            
            if location not in job_location:
                print(f"❌ Location '{location}' NOT in job location '{job_location}'")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Location found in job location")
        
        # 3. EMPLOYMENT TYPE - DAPAT EXACT MATCH (kung may employment type sa alert)
        if self.employment_type and self.employment_type.strip():
            if job.employment_type != self.employment_type.strip():
                print(f"❌ Employment type mismatch: job='{job.employment_type}', alert='{self.employment_type}'")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Employment type matches")
        
        # 4. EDUCATION - JOB EDUCATION DAPAT MAS MATAAS O EQUAL (kung may education sa alert)
        if self.education_level and self.education_level.strip():
            education_hierarchy = {
                'NONE': 0,
                'HIGH_SCHOOL': 1,
                'VOCATIONAL': 2,
                'ASSOCIATE': 3,
                'BACHELOR': 4,
                'MASTER': 5,
                'DOCTORATE': 6,
            }
            
            job_edu_level = education_hierarchy.get(job.education_level or 'NONE', 0)
            alert_edu_level = education_hierarchy.get(self.education_level.strip(), 0)
            
            if job_edu_level < alert_edu_level:
                print(f"❌ Education too low: job={job_edu_level}, alert={alert_edu_level}")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Education meets requirement")
        
        # 5. EXPERIENCE - JOB EXPERIENCE DAPAT MAS MABABA O EQUAL (kung may experience sa alert)
        if self.experience_years is not None:
            # Ensure both values are integers
            job_exp = int(job.experience_years) if job.experience_years is not None else 0
            alert_exp = int(self.experience_years)
            
            if job_exp > alert_exp:
                print(f"❌ Experience too high: job={job_exp} years, alert max={alert_exp} years")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Experience meets requirement")
        
        # 6. REMOTE WORK - DAPAT EXACT MATCH (kung may remote setting sa alert)
        if self.is_remote is not None:
            if job.is_remote != self.is_remote:
                print(f"❌ Remote work mismatch: job={job.is_remote}, alert={self.is_remote}")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Remote work matches")
        
        # 7. CATEGORY - DAPAT EXACT MATCH (kung may category sa alert)
        if self.category:
            job_category_id = job.category.id if job.category else None
            if not job.category or job.category.id != self.category.id:
                print(f"❌ Category mismatch: job category={job_category_id}, alert category={self.category.id}")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            else:
                print(f"✅ Category matches")
        
        # 8. SALARY - DAPAT NASA LOOB NG RANGE (kung may salary sa alert)
        if self.min_salary or self.max_salary:
            # Check minimum salary
            if self.min_salary and (not job.salary_min or job.salary_min < self.min_salary):
                print(f"❌ Salary too low: job min={job.salary_min}, alert min={self.min_salary}")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            
            # Check maximum salary
            if self.max_salary and (not job.salary_max or job.salary_max > self.max_salary):
                print(f"❌ Salary too high: job max={job.salary_max}, alert max={self.max_salary}")
                return False  # ❌ HINDI MATCH, WALANG EMAIL
            
            print(f"✅ Salary meets requirements")
        
        print(f"🎉 ALL CRITERIA MATCH! Sending email...")
        return True  # ✅ MATCH, MAG-EEMAIL
    
    def get_matching_jobs(self):
        Job = apps.get_model('jobs', 'Job')
        jobs = Job.objects.filter(is_active=True)
        
        matching_jobs = []
        for job in jobs:
            if self.does_job_match(job):
                matching_jobs.append(job)
        
        return sorted(matching_jobs, key=lambda x: x.created_at, reverse=True)
    
    def save(self, *args, send_email=True, **kwargs):
        if not self.name or self.name == 'My Job Alert':
            parts = []
            if self.keyword:
                parts.append(self.keyword)
            if self.location:
                parts.append(f"in {self.location}")
            if self.employment_type:
                for value, label in Job.EMPLOYMENT_TYPE_CHOICES:
                    if value == self.employment_type:
                        parts.append(f"({label})")
                        break
            
            self.name = " ".join(parts) if parts else "My Job Alert"
        
        super().save(*args, **kwargs)
    
    def should_send_scheduled_email(self):
        if not self.email_notifications or not self.is_active:
            return False
        
        if not self.last_sent:
            return True
        
        now = timezone.now()
        time_since_last = now - self.last_sent
        
        if self.frequency == 'DAILY':
            return time_since_last.total_seconds() >= 86400
        elif self.frequency == 'WEEKLY':
            return time_since_last.days >= 7
        
        return False
    
    def send_email_notification(self):
        if not self.email_notifications or not self.is_active:
            return 0
        
        matching_jobs = self.get_matching_jobs()
        if not matching_jobs:
            return 0
        
        try:
            user = self.job_seeker
            site_name = getattr(settings, 'SITE_NAME', 'JobBoard')
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            
            if self.frequency == 'DAILY':
                subject = f"Daily Job Alert: {len(matching_jobs)} Jobs Matching '{self.name}'"
            else:
                subject = f"Weekly Job Alert: {len(matching_jobs)} Jobs Matching '{self.name}'"
            
            text_content = f"""Hello {user.first_name or user.username},

Here are your {self.frequency.lower()} job matches for "{self.name}". We found {len(matching_jobs)} jobs that match your criteria.

Recent Jobs:
"""
            
            for job in matching_jobs[:5]:
                text_content += f"""
• {job.title} at {job.company.name}
  Location: {job.location} {'(Remote)' if job.is_remote else ''}
  Type: {job.get_employment_type_display()}
  Salary: {job.get_salary_range()}
  View: {site_url}{job.get_absolute_url()}
"""
            
            text_content += f"""
View all {len(matching_jobs)} matching jobs: {site_url}/jobs/?alert={self.id}

Manage your alerts: {site_url}/job-alerts/

Best regards,
{site_name} Team
"""
            
            print(f"📧 Sending scheduled email to {user.email}")
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            self.last_sent = timezone.now()
            self.save(update_fields=['last_sent'])
            
            return len(matching_jobs)
            
        except Exception as e:
            print(f"❌ Error sending scheduled email: {e}")
            return 0
    
    def send_single_job_email(self, job):
        if not self.email_notifications or not self.is_active:
            print(f"❌ Email notifications disabled or alert inactive")
            return False
        
        try:
            user = self.job_seeker
            site_name = getattr(settings, 'SITE_NAME', 'JobBoard')
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            
            subject = f"New Job Match: {job.title} at {job.company.name}"
            
            clean_description = job.description[:300].replace('\n', ' ').strip()
            if len(job.description) > 300:
                clean_description += "..."
            
            text_content = f"""Hello {user.first_name or user.username},

We found a NEW job that matches your alert "{self.name}":

JOB DETAILS
-----------
Position: {job.title}
Company: {job.company.name}
Location: {job.location} {'(Remote)' if job.is_remote else ''}
Job Type: {job.get_employment_type_display()}
Salary: {job.get_salary_range()}
Education Required: {job.get_education_level_display()}
Experience Required: {job.get_experience_display()}

Job Description:
{clean_description}

APPLY NOW
---------
View full job details and apply here:
{site_url}{job.get_absolute_url()}

Posted: {job.created_at.strftime('%B %d, %Y')}
Deadline: {job.deadline.strftime('%B %d, %Y') if job.deadline else 'Open until filled'}

---

Manage your job alerts: {site_url}/job-alerts/
Unsubscribe from this alert: {site_url}/job-alerts/{self.id}/edit/

Best regards,
{site_name} Team
"""
            
            print(f"📧 Sending email to {user.email}")
            print(f"📧 From: {settings.DEFAULT_FROM_EMAIL}")
            print(f"📧 Subject: {subject}")
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            print(f"✅ Email sent successfully to {user.email}")
            
            self.last_sent = timezone.now()
            self.save(update_fields=['last_sent'])
            
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False

from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_initial_categories(sender, **kwargs):
    if sender.name == 'jobs':
        try:
            if JobCategory.objects.count() == 0:
                categories = [
                    ('Information Technology', 'IT and software development jobs'),
                    ('Marketing', 'Marketing, advertising, and PR'),
                    ('Sales', 'Sales and business development'),
                    ('Finance', 'Finance, accounting, and banking'),
                    ('Human Resources', 'HR, recruitment, and talent management'),
                    ('Engineering', 'Engineering and technical roles'),
                    ('Healthcare', 'Medical, healthcare, and wellness'),
                    ('Education', 'Teaching, training, and education'),
                    ('Design', 'Creative, design, and multimedia'),
                    ('Customer Service', 'Customer support and service'),
                    ('Operations', 'Operations and logistics'),
                    ('Management', 'Management and leadership'),
                    ('Administrative', 'Administrative and clerical'),
                    ('Manufacturing', 'Manufacturing and production'),
                    ('Retail', 'Retail and merchandising'),
                    ('Hospitality', 'Hospitality, tourism, and food service'),
                    ('Legal', 'Legal and compliance'),
                    ('Construction', 'Construction and trades'),
                    ('Transportation', 'Transportation and delivery'),
                    ('Non-Profit', 'Non-profit and social services'),
                ]
                
                for name, description in categories:
                    JobCategory.objects.get_or_create(
                        name=name,
                        defaults={'description': description, 'slug': slugify(name)}
                    )
        except Exception as e:
            print(f"Error creating categories: {e}")