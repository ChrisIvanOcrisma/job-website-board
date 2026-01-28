# applications/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import transaction
import json
import csv
import xlwt
from datetime import datetime
from .forms import SimpleInterviewForm, ApplicationStatusForm
from .models import Application, Interview, ApplicationStatusHistory
from jobs.models import Job
from users.views import JobSeekerRequiredMixin, EmployerRequiredMixin
from .forms import ApplicationForm
from django.core.exceptions import PermissionDenied

class ApplicationListView(LoginRequiredMixin, ListView):
    model = Application
    template_name = 'applications/application_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        job_id = self.kwargs.get('job_id')
        
        if job_id:
            queryset = Application.objects.filter(job_id=job_id)
        else:
            if self.request.user.is_job_seeker():
                queryset = Application.objects.filter(applicant=self.request.user)
            elif self.request.user.is_employer():
                from companies.models import Company
                try:
                    company = Company.objects.get(employer=self.request.user)
                    queryset = Application.objects.filter(job__company=company)
                except Company.DoesNotExist:
                    queryset = Application.objects.none()
            else:
                queryset = Application.objects.none()
        
        return queryset.select_related('applicant', 'job')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_id = self.kwargs.get('job_id')
        
        if job_id:
            context['job'] = get_object_or_404(Job, id=job_id)
        
        queryset = self.get_queryset()
        context['total_applications'] = queryset.count()
        context['new_applications'] = queryset.filter(status='RECEIVED').count()
        context['shortlisted_count'] = queryset.filter(status='SHORTLISTED').count()
        context['hired_count'] = queryset.filter(status='HIRED').count()
        
        return context

# PALITAN ANG ApplicationCreateView NG View-BASED IMPLEMENTATION
class ApplicationCreateView(View):
    template_name = 'applications/application_form.html'
    form_class = ApplicationForm
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        # Check if user is job seeker
        if not request.user.is_job_seeker():
            messages.error(request, 'Only job seekers can apply for jobs.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        job = get_object_or_404(Job, id=self.kwargs['job_id'])
        
        # Check if user has already applied
        if Application.objects.filter(applicant=request.user, job=job).exists():
            messages.warning(request, 'You have already applied for this job.')
            return redirect('job_detail', slug=job.slug)
        
        # Initialize form with user data
        initial_data = self.get_initial_data(request.user)
        form = self.form_class(initial=initial_data)
        
        return render(request, self.template_name, {
            'form': form,
            'job': job,
            'user': request.user
        })
    
    def post(self, request, *args, **kwargs):
        job = get_object_or_404(Job, id=self.kwargs['job_id'])
        
        # Check if already applied
        if Application.objects.filter(applicant=request.user, job=job).exists():
            messages.warning(request, 'You have already applied for this job.')
            return redirect('job_detail', slug=job.slug)
        
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Create application
                application = form.save(commit=False)
                application.job = job
                application.applicant = request.user
                application.status = 'PENDING'
                
                # Set user profile info
                user = request.user
                
                if hasattr(user, 'jobseekerprofile'):
                    profile = user.jobseekerprofile
                    if not application.full_name:
                        application.full_name = profile.full_name or f"{user.first_name} {user.last_name}"
                    if not application.email:
                        application.email = user.email
                    if not application.phone:
                        application.phone = profile.phone or ''
                    if not application.location:
                        application.location = profile.location or ''
                    
                    # Add other fields from profile
                    application.current_position = profile.current_position or 'Not specified'
                    application.skills = profile.skills_text or 'Not specified'
                    application.education_level = profile.education_level or 'BACHELOR'
                    application.degree = profile.degree or 'Not specified'
                    application.university = profile.university or 'Not specified'
                else:
                    # Use basic user info
                    if not application.full_name:
                        application.full_name = f"{user.first_name} {user.last_name}"
                    if not application.email:
                        application.email = user.email
                    application.current_position = 'Not specified'
                    application.skills = 'Not specified'
                    application.education_level = 'BACHELOR'
                    application.degree = 'Not specified'
                    application.university = 'Not specified'
                
                application.save()
                
                # Send application confirmation email
                try:
                    from .emails import send_application_status_email
                    send_application_status_email(application)
                except Exception as e:
                    print(f"Email sending failed: {e}")
                
                messages.success(request, 'Application submitted successfully!')
                return redirect('application_detail', pk=application.pk)
                
            except Exception as e:
                messages.error(request, f'Error submitting application: {str(e)}')
        else:
            # Form has errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        # Return form with errors and entered data
        return render(request, self.template_name, {
            'form': form,
            'job': job,
            'user': request.user
        })
    
    def get_initial_data(self, user):
        """Get initial data for form pre-fill"""
        initial = {}
        
        if hasattr(user, 'jobseekerprofile'):
            profile = user.jobseekerprofile
            initial.update({
                'full_name': profile.full_name or f"{user.first_name} {user.last_name}",
                'email': user.email,
                'phone': profile.phone or '',
                'location': profile.location or '',
            })
        else:
            initial.update({
                'full_name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'phone': '',
                'location': '',
            })
        
        return initial

class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = 'applications/application_detail.html'
    context_object_name = 'application'
    
    def get_queryset(self):
        if self.request.user.is_job_seeker():
            return Application.objects.filter(applicant=self.request.user)
        elif self.request.user.is_employer():
            from companies.models import Company
            try:
                company = Company.objects.get(employer=self.request.user)
                return Application.objects.filter(job__company=company)
            except Company.DoesNotExist:
                return Application.objects.none()
        return Application.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['applicant_user'] = self.object.applicant
        context['can_withdraw'] = self.object.can_withdraw
        
        # Get upcoming interview if any
        context['interview'] = self.object.interviews.filter(
            interview_date__gte=timezone.now().date()
        ).first()
        
        # Check if employer can schedule interview
        if self.request.user.is_employer():
            context['can_schedule_interview'] = self.object.status in ['SHORTLISTED', 'REVIEWED', 'PENDING']
        
        return context

class ApplicationUpdateView(JobSeekerRequiredMixin, UpdateView):
    model = Application
    template_name = 'applications/application_form.html'
    fields = ['cover_letter', 'resume', 'expected_salary', 'notice_period']
    
    def get_queryset(self):
        return Application.objects.filter(applicant=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Application updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('application_detail', kwargs={'pk': self.object.pk})

class ApplicationDeleteView(JobSeekerRequiredMixin, DeleteView):
    model = Application
    template_name = 'applications/application_confirm_delete.html'
    success_url = reverse_lazy('application_list')
    
    def get_queryset(self):
        return Application.objects.filter(applicant=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Application deleted successfully!')
        return super().delete(request, *args, **kwargs)

class ApplicationWithdrawView(JobSeekerRequiredMixin, View):
    """Allow job seeker to withdraw their application"""
    
    def get(self, request, pk):
        # Render confirmation page for withdrawal
        application = get_object_or_404(Application, pk=pk, applicant=request.user)
        
        if not application.can_withdraw:
            messages.error(request, 'This application cannot be withdrawn.')
            return redirect('application_detail', pk=application.pk)
        
        return render(request, 'applications/application_withdraw_confirm.html', {
            'application': application
        })
    
    def post(self, request, pk):
        application = get_object_or_404(Application, pk=pk, applicant=request.user)
        
        # Check if can be withdrawn
        if not application.can_withdraw:
            messages.error(request, 'This application cannot be withdrawn.')
            return redirect('application_detail', pk=application.pk)
        
        # Get withdrawal reason
        reason = request.POST.get('reason', '')
        
        # Check if send email is selected
        send_email = request.POST.get('send_email', 'on') == 'on'
        
        # Withdraw the application
        success, message = application.withdraw(
            reason=reason,
            changed_by=request.user,
            send_email=send_email
        )
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('application_detail', pk=application.pk)

@require_POST
@login_required
def withdraw_application_api(request, pk):
    """API endpoint for withdrawing application (for AJAX requests)"""
    try:
        application = get_object_or_404(Application, pk=pk, applicant=request.user)
        
        if not application.can_withdraw:
            return JsonResponse({
                'success': False,
                'message': 'This application cannot be withdrawn.'
            })
        
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        # Withdraw the application
        success, message = application.withdraw(
            reason=reason,
            changed_by=request.user
        )
        
        return JsonResponse({
            'success': success,
            'message': message,
            'status': application.status,
            'status_display': application.get_status_display(),
            'withdrawn_at': application.withdrawn_at.strftime('%Y-%m-%d %H:%M:%S') if application.withdrawn_at else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

class ApplicationReactivateView(JobSeekerRequiredMixin, View):
    """Allow job seeker to reactivate a withdrawn application"""
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, pk):
        application = get_object_or_404(Application, pk=pk, applicant=request.user)
        
        if application.status != 'WITHDRAWN':
            messages.error(request, 'Only withdrawn applications can be reactivated.')
            return redirect('application_detail', pk=application.pk)
        
        # Check if job is still active
        if not application.job.is_active:
            messages.error(request, 'Cannot reactivate application. The job is no longer active.')
            return redirect('application_detail', pk=application.pk)
        
        # Check if application deadline has passed
        if application.job.application_deadline and application.job.application_deadline < timezone.now():
            messages.error(request, 'Cannot reactivate application. The application deadline has passed.')
            return redirect('application_detail', pk=application.pk)
        
        # Reactivate application (set back to PENDING)
        old_status = application.status
        application.status = 'PENDING'
        application.withdraw_reason = None
        application.withdrawn_at = None
        application.save()
        
        # Create status history
        ApplicationStatusHistory.objects.create(
            application=application,
            old_status=old_status,
            new_status='PENDING',
            changed_by=request.user,
            notes='Application reactivated by applicant'
        )
        
        # Send reactivation email
        try:
            from .emails import send_application_status_email
            send_application_status_email(application, old_status)
        except Exception as e:
            print(f"Email sending failed: {e}")
        
        messages.success(request, 'Application reactivated successfully.')
        return redirect('application_detail', pk=application.pk)

class ApplicationStatusUpdateView(EmployerRequiredMixin, View):
    """Update application status - includes interview scheduling and auto-Monday for HIRED"""
    template_name = 'applications/update_status.html'
    
    def get(self, request, pk):
        application = get_object_or_404(Application, pk=pk)
        
        # Verify employer owns this application's job
        from companies.models import Company
        try:
            company = Company.objects.get(employer=request.user)
            if application.job.company != company:
                messages.error(request, "You don't have permission to update this application.")
                return redirect('application_detail', pk=application.pk)
        except Company.DoesNotExist:
            messages.error(request, "You don't have a company.")
            return redirect('application_detail', pk=application.pk)
        
        # Get pre-selected status from URL (optional)
        pre_selected_status = request.GET.get('status', '')
        
        # Prepare interview form if needed
        interview_form = None
        if pre_selected_status == 'INTERVIEW':
            interview_form = SimpleInterviewForm()
        
        return render(request, self.template_name, {
            'application': application,
            'pre_selected_status': pre_selected_status,
            'interview_form': interview_form,
        })
    
    def post(self, request, pk):
        application = get_object_or_404(Application, pk=pk)
        
        # Verify employer owns this application's job
        from companies.models import Company
        try:
            company = Company.objects.get(employer=request.user)
            if application.job.company != company:
                messages.error(request, "You don't have permission to update this application.")
                return redirect('application_detail', pk=application.pk)
        except Company.DoesNotExist:
            messages.error(request, "You don't have a company.")
            return redirect('application_detail', pk=application.pk)
        
        # Get form data
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        send_email = request.POST.get('send_email') == 'on'
        
        # Validate status
        if not new_status:
            messages.error(request, "Please select a status.")
            return redirect('update_status', pk=application.pk)
        
        # ============ HANDLE INTERVIEW SCHEDULING ============
        if new_status == 'INTERVIEW':
            interview_date = request.POST.get('interview_date')
            interview_time = request.POST.get('interview_time')
            location = request.POST.get('location')
            
            # Validate interview details
            if not interview_date or not interview_time or not location:
                messages.error(request, "Please provide interview date, time, and location.")
                interview_form = SimpleInterviewForm(request.POST)
                return render(request, self.template_name, {
                    'application': application,
                    'pre_selected_status': 'INTERVIEW',
                    'interview_form': interview_form,
                })
            
            # Create interview record
            try:
                interview = Interview.objects.create(
                    application=application,
                    interview_date=interview_date,
                    interview_time=interview_time,
                    location=location,
                    scheduled_by=request.user
                )
                
                # Update application status
                application.update_status(
                    new_status='INTERVIEW',
                    changed_by=request.user,
                    notes=f"Interview scheduled for {interview_date} at {interview_time}. Location: {location}",
                    send_email=send_email
                )
                
                # Send interview email if requested
                if send_email:
                    from .emails import send_simple_interview_email
                    send_simple_interview_email(interview)
                
                messages.success(request, "Interview scheduled successfully!")
                return redirect('application_detail', pk=application.pk)
                
            except Exception as e:
                messages.error(request, f"Error scheduling interview: {str(e)}")
                interview_form = SimpleInterviewForm(request.POST)
                return render(request, self.template_name, {
                    'application': application,
                    'pre_selected_status': 'INTERVIEW',
                    'interview_form': interview_form,
                })
        
        # ============ HANDLE HIRED STATUS ============
        elif new_status == 'HIRED':
            try:
                # Calculate next Monday
                from datetime import datetime, timedelta
                today = datetime.now().date()
                days_ahead = 0 - today.weekday()  # Monday is 0
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                next_monday = today + timedelta(days=days_ahead)
                
                # Save hired details to application
                application.hire_start_date = next_monday
                application.hire_location = "Main Office - HR Department"  # Default location
                application.hire_instructions = "Please arrive by 8:00 AM. Bring original documents and ask for HR at reception."
                application.hired_at = timezone.now()
                application.save()
                
                # Update application status to HIRED (but don't send basic email)
                old_status = application.status
                application.status = 'HIRED'
                application.save()
                
                # Create status history
                ApplicationStatusHistory.objects.create(
                    application=application,
                    old_status=old_status,
                    new_status='HIRED',
                    changed_by=request.user,
                    notes=f"Hired! Auto-scheduled start date: Monday, {next_monday.strftime('%B %d, %Y')}"
                )
                
                # Send detailed hired email if requested
                if send_email:
                    try:
                        from .emails import send_hired_details_email
                        send_hired_details_email(application)
                        print(f"✅ Hired email sent to {application.email}")
                        print(f"   Start date: Monday, {next_monday.strftime('%B %d, %Y')}")
                    except Exception as e:
                        print(f"❌ Hired email sending failed: {e}")
                else:
                    print(f"ℹ️ Email sending disabled for HIRED status")
                
                messages.success(request, f"Candidate hired! Start date: Monday, {next_monday.strftime('%B %d, %Y')}")
                return redirect('application_detail', pk=application.pk)
                
            except Exception as e:
                messages.error(request, f"Error processing hire: {str(e)}")
                return render(request, self.template_name, {
                    'application': application,
                    'pre_selected_status': 'HIRED',
                })
        
        # ============ REGULAR STATUS UPDATES ============
        else:
            # Regular status update (not interview or hired)
            application.update_status(
                new_status=new_status,
                changed_by=request.user,
                notes=notes,
                send_email=send_email
            )
            
            messages.success(request, f"Status updated to {application.get_status_display()}")
            return redirect('application_detail', pk=application.pk)

# =================== EXPORT FUNCTIONS ===================

@login_required
def export_applications_csv(request, job_slug=None):
    """Export applications to CSV"""
    if job_slug:
        job = get_object_or_404(Job, slug=job_slug, company=request.user.company)
        base_query = job.applications.all()
        filename = f"applications_{job.slug}.csv"
    else:
        from companies.models import Company
        try:
            company = Company.objects.get(employer=request.user)
            base_query = Application.objects.filter(job__company=company)
            filename = f"all_applications_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        except Company.DoesNotExist:
            return HttpResponse("Company not found", status=404)
    
    # Check if specific applications are selected
    selected_ids = request.GET.get('selected', '').split(',')
    if selected_ids and selected_ids[0]:
        applications = base_query.filter(id__in=selected_ids)
        filename = f"selected_applications_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    else:
        applications = base_query
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'ID', 'Applicant Name', 'Email', 'Phone', 'Job Title',
        'Applied Date', 'Status', 'Current Position', 'Skills',
        'Education Level', 'Degree', 'University', 'Location',
        'Expected Salary', 'Notice Period', 'Cover Letter'
    ])
    
    # Write data
    for app in applications:
        writer.writerow([
            app.id,
            app.full_name or f"{app.applicant.username}",
            app.email or app.applicant.email,
            app.phone or '',
            app.job.title,
            app.applied_at.strftime('%Y-%m-%d %H:%M:%S'),
            app.get_status_display(),
            app.current_position or '',
            app.skills or '',
            app.get_education_level_display() if app.education_level else '',
            app.degree or '',
            app.university or '',
            app.location or '',
            app.expected_salary or '',
            app.notice_period or '',
            (app.cover_letter[:100] + '...') if app.cover_letter else ''
        ])
    
    return response

@login_required
def export_applications_excel(request, job_slug=None):
    """Export applications to Excel"""
    if job_slug:
        job = get_object_or_404(Job, slug=job_slug, company=request.user.company)
        base_query = job.applications.all()
        filename = f"applications_{job.slug}.xls"
    else:
        from companies.models import Company
        try:
            company = Company.objects.get(employer=request.user)
            base_query = Application.objects.filter(job__company=company)
            filename = f"all_applications_{datetime.now().strftime('%Y%m%d_%H%M')}.xls"
        except Company.DoesNotExist:
            return HttpResponse("Company not found", status=404)
    
    # Check if specific applications are selected
    selected_ids = request.GET.get('selected', '').split(',')
    if selected_ids and selected_ids[0]:
        applications = base_query.filter(id__in=selected_ids)
        filename = f"selected_applications_{datetime.now().strftime('%Y%m%d_%H%M')}.xls"
    else:
        applications = base_query
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Applications')
    
    # Header style
    header_style = xlwt.easyxf(
        'font: bold on; align: wrap on, vert centre, horiz center'
    )
    
    # Column headers
    headers = [
        'ID', 'Applicant Name', 'Email', 'Phone', 'Job Title',
        'Applied Date', 'Status', 'Current Position', 'Skills',
        'Education Level', 'Degree', 'University', 'Location',
        'Expected Salary', 'Notice Period', 'Cover Letter'
    ]
    
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_style)
        # Set column widths
        if col in [0]:  # ID
            ws.col(col).width = 2000
        elif col in [5, 14]:  # Applied Date, Notice Period
            ws.col(col).width = 4000
        elif col == 15:  # Cover Letter
            ws.col(col).width = 8000
        else:
            ws.col(col).width = 5000
    
    # Data rows
    for row, app in enumerate(applications, start=1):
        ws.write(row, 0, app.id)
        ws.write(row, 1, app.full_name or f"{app.applicant.username}")
        ws.write(row, 2, app.email or app.applicant.email)
        ws.write(row, 3, app.phone or '')
        ws.write(row, 4, app.job.title)
        ws.write(row, 5, app.applied_at.strftime('%Y-%m-%d %H:%M:%S'))
        ws.write(row, 6, app.get_status_display())
        ws.write(row, 7, app.current_position or '')
        ws.write(row, 8, app.skills or '')
        ws.write(row, 9, app.get_education_level_display() if app.education_level else '')
        ws.write(row, 10, app.degree or '')
        ws.write(row, 11, app.university or '')
        ws.write(row, 12, app.location or '')
        ws.write(row, 13, app.expected_salary or '')
        ws.write(row, 14, app.notice_period or '')
        ws.write(row, 15, app.cover_letter or '')
    
    wb.save(response)
    return response

# =================== BULK UPDATE FUNCTION ===================

@login_required
@require_POST
def bulk_update_applications(request):
    """Handle bulk updates for applications"""
    try:
        selected_ids = request.POST.get('selected_ids', '').split(',')
        status = request.POST.get('status')
        send_emails = request.POST.get('send_emails', 'false') == 'true'
        
        # Filter applications that belong to user's company
        from companies.models import Company
        company = get_object_or_404(Company, employer=request.user)
        
        applications = Application.objects.filter(
            id__in=selected_ids,
            job__company=company
        )
        
        updated_count = 0
        email_count = 0
        
        # Update status if provided
        if status:
            for app in applications:
                old_status = app.status
                if old_status != status:
                    # Update with email option
                    app.update_status(
                        new_status=status,
                        changed_by=request.user,
                        notes='Bulk status update',
                        send_email=send_emails
                    )
                    updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated': updated_count,
            'emails_sent': email_count,
            'message': f'Updated {updated_count} application(s)'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    

class ScheduleInterviewSimpleView(EmployerRequiredMixin, View):
    """Simple interview scheduling - date, time, location only"""
    template_name = 'applications/schedule_interview_simple.html'
    
    def get_application(self, pk):
        """Get application and verify employer owns it"""
        application = get_object_or_404(Application, pk=pk)
        
        # Verify employer owns this application's job
        if not hasattr(self.request.user, 'company'):
            raise PermissionDenied
        
        if application.job.company != self.request.user.company:
            raise PermissionDenied
        
        return application
    
    def get(self, request, pk):
        application = self.get_application(pk)
        
        # Check if application can have interview scheduled
        if application.status not in ['SHORTLISTED', 'REVIEWED', 'PENDING']:
            messages.warning(
                request, 
                f"Cannot schedule interview for this application status."
            )
            return redirect('application_detail', pk=application.pk)
        
        form = SimpleInterviewForm()
        
        return render(request, self.template_name, {
            'form': form,
            'application': application,
            'job': application.job,
            'applicant': application.applicant,
        })
    
    def post(self, request, pk):
        application = self.get_application(pk)
        form = SimpleInterviewForm(request.POST)
        
        if form.is_valid():
            try:
                # Check if send email is selected
                send_email = request.POST.get('send_email', 'on') == 'on'
                
                # Create interview
                interview = form.save(commit=False)
                interview.application = application
                interview.scheduled_by = request.user
                interview.save()
                
                # Update application status to INTERVIEW
                old_status = application.status
                application.update_status(
                    new_status='INTERVIEW',
                    changed_by=request.user,
                    notes=f"Interview scheduled for {interview.interview_date}",
                    send_email=send_email
                )
                
                # Send interview email if requested
                if send_email:
                    try:
                        from .emails import send_simple_interview_email
                        send_simple_interview_email(interview)
                    except Exception as e:
                        print(f"Interview email sending failed: {e}")
                
                messages.success(request, "Interview scheduled successfully!")
                return redirect('application_detail', pk=application.pk)
                
            except Exception as e:
                messages.error(request, f"Error scheduling interview: {str(e)}")
        
        return render(request, self.template_name, {
            'form': form,
            'application': application,
            'job': application.job,
            'applicant': application.applicant,
        })

# =================== URL PATTERNS TO ADD ===================
"""
# Add these to your urls.py

# Export URLs
path('applications/export/csv/', views.export_applications_csv, name='export_applications_csv'),
path('applications/export/excel/', views.export_applications_excel, name='export_applications_excel'),
path('applications/<slug:job_slug>/export/csv/', views.export_applications_csv, name='export_job_applications_csv'),
path('applications/<slug:job_slug>/export/excel/', views.export_applications_excel, name='export_job_applications_excel'),

# Bulk update URL
path('applications/bulk-update/', views.bulk_update_applications, name='bulk_update_applications'),

# Withdrawal URLs
path('applications/<int:pk>/withdraw/', views.ApplicationWithdrawView.as_view(), name='application_withdraw'),
path('api/applications/<int:pk>/withdraw/', views.withdraw_application_api, name='withdraw_application_api'),
path('applications/<int:pk>/reactivate/', views.ApplicationReactivateView.as_view(), name='application_reactivate'),

# Interview scheduling
path('applications/<int:pk>/schedule-interview/', views.ScheduleInterviewSimpleView.as_view(), name='schedule_interview_simple'),
"""