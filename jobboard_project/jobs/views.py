from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count
from django_filters.views import FilterView
from users.views import EmployerRequiredMixin, JobSeekerRequiredMixin
from .models import Job, JobCategory, JobTag, SavedJob, JobAlert, ScreeningQuestion
from .forms import JobForm, JobFilterForm, JobAlertForm, ScreeningQuestionForm
from .filters import JobFilter
from analytics.models import JobView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
import logging

# Setup logger for debugging
logger = logging.getLogger(__name__)

class JobListView(FilterView):
    model = Job
    template_name = 'jobs/job_list.html'
    filterset_class = JobFilter
    paginate_by = 20
    context_object_name = 'jobs'
    
    def get_queryset(self):
        queryset = Job.objects.filter(is_active=True).select_related('company')
        
        keyword = self.request.GET.get('keyword', '')
        location = self.request.GET.get('location', '')
        remote = self.request.GET.get('remote', '')
        education_level = self.request.GET.get('education_level', '')
        experience = self.request.GET.get('experience', '')
        
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(requirements__icontains=keyword) |
                Q(qualifications__icontains=keyword) |
                Q(skills__icontains=keyword)
            )
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if remote == 'true':
            queryset = queryset.filter(is_remote=True)
        
        if education_level:
            queryset = queryset.filter(education_level=education_level)
        
        if experience:
            try:
                experience_years = int(experience)
                queryset = queryset.filter(experience_years=experience_years)
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = JobCategory.objects.annotate(
            job_count=Count('job')
        ).order_by('-job_count')[:10]
        context['popular_tags'] = JobTag.objects.annotate(
            job_count=Count('job')
        ).order_by('-job_count')[:15]
        return context

class JobDetailView(DetailView):
    model = Job
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Track the view
        try:
            # Create session if it doesn't exist (for anonymous users)
            if not self.request.session.session_key:
                self.request.session.create()
            
            if self.request.user.is_authenticated:
                # For authenticated users - track with user
                JobView.objects.create(
                    job=obj,
                    viewer=self.request.user,
                    ip_address=self.request.META.get('REMOTE_ADDR')
                )
            else:
                # For anonymous users - track with session key
                session_key = self.request.session.session_key
                JobView.objects.create(
                    job=obj,
                    session_key=session_key,
                    ip_address=self.request.META.get('REMOTE_ADDR')
                )
            
            # Increment view count on the job
            obj.views += 1
            obj.save(update_fields=['views'])
            
        except Exception as e:
            # Log error but don't crash the page
            print(f"Error tracking view: {e}")
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object
        
        # Process skills list
        if job.skills:
            context['skills_list'] = [skill.strip() for skill in job.skills.split(',')]
        else:
            context['skills_list'] = []
        
        # Check if job is saved (for job seekers)
        if self.request.user.is_authenticated and hasattr(self.request.user, 'role') and self.request.user.role == 'JOB_SEEKER':
            context['is_saved'] = SavedJob.objects.filter(
                job_seeker=self.request.user,
                job=job
            ).exists()
        else:
            context['is_saved'] = False
        
        # Check if user has applied (for job seekers)
        if self.request.user.is_authenticated and hasattr(self.request.user, 'role') and self.request.user.role == 'JOB_SEEKER':
            try:
                from applications.models import Application
                context['has_applied'] = Application.objects.filter(
                    applicant=self.request.user,
                    job=job
                ).exists()
            except:
                context['has_applied'] = False
        else:
            context['has_applied'] = False
        
        # Get similar jobs
        similar_jobs = Job.objects.filter(
            Q(category=job.category) | 
            Q(skills__icontains=job.skills)
        ).exclude(id=job.id).filter(is_active=True).select_related('company')[:5]
        context['similar_jobs'] = similar_jobs
        
        return context
class JobCreateView(EmployerRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'
    
    def form_valid(self, form):
        from companies.models import Company
        try:
            company = Company.objects.get(employer=self.request.user)
        except Company.DoesNotExist:
            messages.error(self.request, 'You need to create a company profile before posting jobs.')
            return redirect('company_create')
        
        form.instance.company = company
        
        # DEBUG LOG
        logger.info(f"🔍 DEBUG: JobCreateView - Creating new job: {form.cleaned_data.get('title')}")
        print(f"🔍 DEBUG: JobCreateView - Creating new job: {form.cleaned_data.get('title')}")
        
        if 'education_level' in self.request.POST:
            form.instance.education_level = self.request.POST.get('education_level')
        if 'experience_years' in self.request.POST:
            try:
                form.instance.experience_years = int(self.request.POST.get('experience_years'))
            except (ValueError, TypeError):
                form.instance.experience_years = 0
        if 'qualifications' in self.request.POST:
            form.instance.qualifications = self.request.POST.get('qualifications')
        if 'skills' in self.request.POST:
            form.instance.skills = self.request.POST.get('skills')
        if 'benefits' in self.request.POST:
            form.instance.benefits = self.request.POST.get('benefits')
        
        messages.success(self.request, 'Job posted successfully!')
        
        # Save the form first
        response = super().form_valid(form)
        
        # DEBUG: Check if check_job_alerts was called
        print(f"🔍 DEBUG: Job created successfully with ID: {self.object.id}")
        print(f"🔍 DEBUG: Job title: {self.object.title}")
        print(f"🔍 DEBUG: Job active: {self.object.is_active}")
        print(f"🔍 DEBUG: Job location: {self.object.location}")
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('job_detail', kwargs={'slug': self.object.slug})

class JobUpdateView(EmployerRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'
    
    def get_queryset(self):
        from companies.models import Company
        company = get_object_or_404(Company, employer=self.request.user)
        return Job.objects.filter(company=company)
    
    def form_valid(self, form):
        if 'education_level' in self.request.POST:
            form.instance.education_level = self.request.POST.get('education_level')
        if 'experience_years' in self.request.POST:
            try:
                form.instance.experience_years = int(self.request.POST.get('experience_years'))
            except (ValueError, TypeError):
                form.instance.experience_years = 0
        if 'qualifications' in self.request.POST:
            form.instance.qualifications = self.request.POST.get('qualifications')
        if 'skills' in self.request.POST:
            form.instance.skills = self.request.POST.get('skills')
        if 'benefits' in self.request.POST:
            form.instance.benefits = self.request.POST.get('benefits')
        
        messages.success(self.request, 'Job updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('job_detail', kwargs={'slug': self.object.slug})

class SavedJobsView(JobSeekerRequiredMixin, ListView):
    model = SavedJob
    template_name = 'jobs/saved_jobs.html'
    context_object_name = 'saved_jobs'
    
    def get_queryset(self):
        return SavedJob.objects.filter(job_seeker=self.request.user).select_related('job')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for saved_job in context['saved_jobs']:
            if saved_job.job.skills:
                saved_job.job.skills_list = [skill.strip() for skill in saved_job.job.skills.split(',')]
            else:
                saved_job.job.skills_list = []
        return context

class SaveJobView(JobSeekerRequiredMixin, View):
    def post(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        
        saved_job, created = SavedJob.objects.get_or_create(
            job_seeker=request.user,
            job=job
        )
        
        if created:
            messages.success(request, 'Job saved successfully!')
        else:
            saved_job.delete()
            messages.info(request, 'Job removed from saved list.')
        
        return redirect('job_detail', slug=job.slug)

# =============================================
# JOB ALERT VIEWS (FIXED AND COMPLETE)
# =============================================

class JobAlertsView(JobSeekerRequiredMixin, ListView):
    model = JobAlert
    template_name = 'jobs/job_alerts.html'
    context_object_name = 'alerts'
    
    def get_queryset(self):
        return JobAlert.objects.filter(job_seeker=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = JobCategory.objects.all()
        context['employment_types'] = Job.EMPLOYMENT_TYPE_CHOICES
        context['education_levels'] = Job.EDUCATION_CHOICES
        context['experience_choices'] = Job.EXPERIENCE_CHOICES
        return context

class CreateJobAlertView(JobSeekerRequiredMixin, View):
    template_name = 'jobs/create_job_alert.html'
    
    def get(self, request):
        form = JobAlertForm(user=request.user)
        
        context = {
            'form': form,
            'title': 'Create Job Alert',
            'categories': JobCategory.objects.annotate(job_count=Count('job'))
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = JobAlertForm(request.POST, user=request.user)
        
        if form.is_valid():
            alert = form.save()
            messages.success(request, 'Job alert created successfully!')
            return redirect('job_alerts')
        else:
            context = {
                'form': form,
                'title': 'Create Job Alert',
                'categories': JobCategory.objects.annotate(job_count=Count('job'))
            }
            return render(request, self.template_name, context)

class EditJobAlertView(JobSeekerRequiredMixin, View):
    template_name = 'jobs/edit_job_alert.html'
    
    def get(self, request, alert_id):
        alert = get_object_or_404(JobAlert, id=alert_id, job_seeker=request.user)
        
        form = JobAlertForm(instance=alert, user=request.user)
        
        context = {
            'form': form,
            'alert': alert,
            'title': 'Edit Job Alert',
            'categories': JobCategory.objects.annotate(job_count=Count('job'))
        }
        return render(request, self.template_name, context)
    
    def post(self, request, alert_id):
        alert = get_object_or_404(JobAlert, id=alert_id, job_seeker=request.user)
        
        form = JobAlertForm(request.POST, instance=alert, user=request.user)
        
        if form.is_valid():
            alert = form.save()
            messages.success(request, 'Job alert updated successfully!')
            return redirect('job_alerts')
        else:
            context = {
                'form': form,
                'alert': alert,
                'title': 'Edit Job Alert',
                'categories': JobCategory.objects.annotate(job_count=Count('job'))
            }
            return render(request, self.template_name, context)

class DeleteJobAlertView(JobSeekerRequiredMixin, View):
    def post(self, request, alert_id):
        alert = get_object_or_404(JobAlert, id=alert_id, job_seeker=request.user)
        alert.delete()
        messages.success(request, 'Job alert deleted successfully!')
        return redirect('job_alerts')

class PreviewJobAlertView(JobSeekerRequiredMixin, View):
    template_name = 'jobs/preview_job_alert.html'
    
    def get(self, request, alert_id):
        alert = get_object_or_404(JobAlert, id=alert_id, job_seeker=request.user)
        jobs = alert.get_matching_jobs()
        
        paginator = Paginator(jobs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # DEBUG: Show matching jobs count
        print(f"🔍 DEBUG: PreviewJobAlertView - Alert: {alert.name}")
        print(f"🔍 DEBUG: PreviewJobAlertView - Matching jobs: {jobs.count()}")
        
        context = {
            'alert': alert,
            'jobs': page_obj,
            'job_count': jobs.count(),
            'title': f'Preview: {alert.name}'
        }
        return render(request, self.template_name, context)

# =============================================
# TEST JOB ALERT EMAIL MANUALLY
# =============================================

class TestJobAlertEmailView(JobSeekerRequiredMixin, View):
    """Debug view to test job alert email manually"""
    
    def get(self, request, alert_id):
        alert = get_object_or_404(JobAlert, id=alert_id, job_seeker=request.user)
        
        print(f"🔍 DEBUG: Testing email for alert: {alert.name}")
        print(f"🔍 DEBUG: Alert criteria:")
        print(f"   - Keyword: {alert.keyword}")
        print(f"   - Location: {alert.location}")
        print(f"   - Category: {alert.category}")
        print(f"   - Frequency: {alert.frequency}")
        print(f"   - Email notifications: {alert.email_notifications}")
        print(f"   - Is active: {alert.is_active}")
        
        # Get matching jobs
        matching_jobs = alert.get_matching_jobs()
        print(f"🔍 DEBUG: Matching jobs found: {matching_jobs.count()}")
        
        if matching_jobs.count() > 0:
            print("🔍 DEBUG: First 3 matching jobs:")
            for job in matching_jobs[:3]:
                print(f"   - {job.title} at {job.company.name} ({job.location})")
        
        # Try to send email
        email_sent = alert.send_email_notification()
        
        if email_sent > 0:
            messages.success(request, f'Test email sent successfully! {email_sent} matching jobs found.')
            print(f"✅ DEBUG: Email sent successfully for {email_sent} jobs")
        else:
            messages.warning(request, f'No email sent. {matching_jobs.count()} matching jobs found.')
            print(f"⚠️ DEBUG: No email sent. Matching jobs: {matching_jobs.count()}")
        
        return redirect('job_alerts')

class ForceCheckAlertsView(View):
    """Debug view to force check all alerts for a specific job"""
    
    def get(self, request, job_id):
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can access this page.')
            return redirect('home')
        
        job = get_object_or_404(Job, id=job_id)
        
        print(f"🔍 DEBUG: Force checking alerts for job: {job.title}")
        print(f"🔍 DEBUG: Job details:")
        print(f"   - Title: {job.title}")
        print(f"   - Location: {job.location}")
        print(f"   - Company: {job.company.name}")
        print(f"   - Skills: {job.skills}")
        
        # Manually call check_job_alerts
        job.check_job_alerts()
        
        messages.success(request, f'Manually checked alerts for job: {job.title}')
        return redirect('job_detail', slug=job.slug)

# =============================================
# END OF JOB ALERT VIEWS
# =============================================

class ClearSavedJobsView(JobSeekerRequiredMixin, View):
    def post(self, request):
        saved_jobs = SavedJob.objects.filter(job_seeker=request.user)
        count = saved_jobs.count()
        saved_jobs.delete()
        
        if count > 0:
            messages.success(request, f'Cleared {count} saved jobs.')
        else:
            messages.info(request, 'No saved jobs to clear.')
        
        return redirect('saved_jobs')

class MyApplicationsView(JobSeekerRequiredMixin, ListView):
    template_name = 'jobs/my_applications.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        from applications.models import Application
        return Application.objects.filter(applicant=self.request.user).select_related('job')

class RecommendedJobsView(JobSeekerRequiredMixin, ListView):
    template_name = 'jobs/recommended_jobs.html'
    context_object_name = 'jobs'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        queryset = Job.objects.filter(is_active=True).select_related('company')
        
        if hasattr(user, 'jobseekerprofile'):
            if user.jobseekerprofile.education_level:
                education_order = [choice[0] for choice in Job.EDUCATION_CHOICES]
                if user.jobseekerprofile.education_level in education_order:
                    selected_index = education_order.index(user.jobseekerprofile.education_level)
                    allowed_levels = education_order[selected_index:]
                    queryset = queryset.filter(education_level__in=allowed_levels)
            
            if user.jobseekerprofile.years_experience is not None:
                queryset = queryset.filter(experience_years__lte=user.jobseekerprofile.years_experience)
        
        return queryset.order_by('-created_at')[:100]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for job in context['jobs']:
            if job.skills:
                job.skills_list = [skill.strip() for skill in job.skills.split(',')]
            else:
                job.skills_list = []
        return context

class JobSearchView(View):
    template_name = 'jobs/job_search.html'
    
    def get(self, request):
        form = JobFilterForm(request.GET or None)
        jobs = Job.objects.filter(is_active=True)
        
        if form.is_valid():
            keyword = form.cleaned_data.get('keyword')
            location = form.cleaned_data.get('location')
            category = form.cleaned_data.get('category')
            remote = form.cleaned_data.get('remote')
            education_level = form.cleaned_data.get('education_level')
            experience_years = form.cleaned_data.get('experience_years')
            
            if keyword:
                jobs = jobs.filter(
                    Q(title__icontains=keyword) |
                    Q(description__icontains=keyword) |
                    Q(requirements__icontains=keyword) |
                    Q(qualifications__icontains=keyword) |
                    Q(skills__icontains=keyword)
                )
            
            if location:
                jobs = jobs.filter(location__icontains=location)
            
            if category:
                jobs = jobs.filter(category=category)
            
            if remote:
                jobs = jobs.filter(is_remote=True)
            
            if education_level:
                jobs = jobs.filter(education_level=education_level)
            
            if experience_years is not None:
                jobs = jobs.filter(experience_years=experience_years)
        
        for job in jobs:
            if job.skills:
                job.skills_list = [skill.strip() for skill in job.skills.split(',')]
            else:
                job.skills_list = []
        
        return render(request, self.template_name, {
            'form': form,
            'jobs': jobs,
            'categories': JobCategory.objects.all()
        })

class JobDashboardView(EmployerRequiredMixin, View):
    template_name = 'jobs/employer_dashboard.html'
    
    def get(self, request):
        from companies.models import Company
        from applications.models import Application
        
        company = get_object_or_404(Company, employer=request.user)
        
        total_jobs = Job.objects.filter(company=company).count()
        active_jobs = Job.objects.filter(company=company, is_active=True).count()
        total_views = JobView.objects.filter(job__company=company).count()
        total_applications = Application.objects.filter(job__company=company).count()
        
        education_distribution = Job.objects.filter(
            company=company
        ).values('education_level').annotate(
            count=Count('id')
        ).order_by('education_level')
        
        experience_distribution = Job.objects.filter(
            company=company
        ).values('experience_years').annotate(
            count=Count('id')
        ).order_by('experience_years')
        
        recent_applications = Application.objects.filter(
            job__company=company
        ).select_related('applicant', 'job').order_by('-created_at')[:10]
        
        popular_jobs = Job.objects.filter(
            company=company
        ).annotate(
            view_count=Count('jobview'),
            application_count=Count('application')
        ).order_by('-view_count')[:5]
        
        context = {
            'company': company,
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'total_views': total_views,
            'total_applications': total_applications,
            'education_distribution': education_distribution,
            'experience_distribution': experience_distribution,
            'recent_applications': recent_applications,
            'popular_jobs': popular_jobs,
        }
        
        return render(request, self.template_name, context)