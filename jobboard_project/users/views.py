# users/views.py - COMPLETE UPDATED VERSION
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomLoginForm
from companies.models import Company
from jobs.models import Job, SavedJob
from applications.models import Application
from django.contrib.auth import get_user_model
from django.contrib.auth import logout as auth_logout 
from django.views import View 
from django.contrib.auth.decorators import login_required

class RegisterView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = '/dashboard/'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        
        # Redirect based on role
        if user.is_employer():
            messages.success(self.request, 'Account created! Please set up your company profile.')
            return redirect('company_create')
        elif user.is_job_seeker():
            messages.success(self.request, 'Account created! Welcome to Job Board.')
            return redirect('dashboard')
        
        return response

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'users/login.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {self.request.user.username}!')
        return response

class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        auth_logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('home')

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/dashboard.html'
    
    def get_template_names(self):
        user = self.request.user
        if user.is_admin():
            return ['users/admin_dashboard.html']
        elif user.is_employer():
            return ['users/employer_dashboard.html']
        elif user.is_job_seeker():
            return ['users/jobseeker_dashboard.html']
        return super().get_template_names()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        User = get_user_model()  # Move this to the top
        
        if user.is_admin():
            # Admin dashboard data - COMPLETE SET
            context['total_users'] = User.objects.count()
            context['total_companies'] = Company.objects.count()
            context['total_jobs'] = Job.objects.count()
            context['total_applications'] = Application.objects.count()
            
            # ADD THESE TWO LINES:
            context['recent_users'] = User.objects.order_by('-date_joined')[:10]
            context['needs_attention'] = Job.objects.filter(is_active=False).count()
            
        elif user.is_employer():
            # Employer dashboard data
            try:
                company = Company.objects.get(employer=user)
                jobs = company.jobs.all()
                
                # Calculate all necessary stats
                total_apps = Application.objects.filter(job__company=company).count()
                active_jobs = jobs.filter(is_active=True).count()
                hired_count = Application.objects.filter(
                    job__company=company,
                    status='HIRED'
                ).count()
                recent_apps = Application.objects.filter(
                    job__company=company
                ).order_by('-applied_at')[:5]  # Last 5 applications
                
                context['company'] = company
                context['jobs'] = jobs
                context['applications_count'] = total_apps
                context['active_jobs_count'] = active_jobs
                context['hired_count'] = hired_count
                context['recent_applications'] = recent_apps
                
            except Company.DoesNotExist:
                context['needs_company'] = True
                
        elif user.is_job_seeker():
            # Job seeker dashboard data
            context['applications'] = Application.objects.filter(applicant=user)
            context['saved_jobs'] = SavedJob.objects.filter(job_seeker=user)
            
        return context

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin()

class EmployerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_employer()

class JobSeekerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_job_seeker()
    
from django.contrib.auth import update_session_auth_hash

from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.backends import ModelBackend

@login_required
def edit_profile(request):
    user = request.user
    
    if request.method == 'POST':
        print("=" * 60)
        print("EDIT PROFILE DEBUG:")
        
        # Get old and new username
        old_username = user.username
        new_username = request.POST.get('username', '').strip()
        
        print(f"Old username: {old_username}")
        print(f"New username from form: {new_username}")
        
        username_changed = (new_username and new_username != old_username)
        
        if username_changed:
            user.username = new_username
            print(f"Username changed to: {user.username}")
        
        user.first_name = request.POST.get('first_name', '').strip()
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        print(f"User saved successfully")
        
        if username_changed:
         
            update_session_auth_hash(request, user)
            
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            print("Session updated for new username!")
        
        print("=" * 60)
        
        messages.success(request, '✅ Profile updated successfully!')
        return redirect('users:dashboard')
    
    return render(request, 'users/edit_profile.html', {'user': user})