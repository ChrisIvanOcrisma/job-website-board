from django import forms
from django.utils import timezone
import datetime
from .models import Application, Interview

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['resume', 'cover_letter']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 6}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resume'].widget.attrs['class'] = 'form-control'
        self.fields['cover_letter'].widget.attrs['class'] = 'form-control'
        
        # Set labels
        self.fields['cover_letter'].label = 'Cover Letter (Optional)'
        self.fields['cover_letter'].required = False
    
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
            if not any(resume.name.lower().endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(
                    'Only PDF, DOC, DOCX, and TXT files are allowed.'
                )
            
            # Check file size (5MB max)
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'File size exceeds 5MB limit.'
                )
        
        return resume

class ApplicationStatusForm(forms.ModelForm):
    # Add email notification option
    send_email = forms.BooleanField(
        initial=True,
        required=False,
        label="Send email notification to applicant",
        help_text="Applicant will be notified of status change via email"
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this status change'}),
        required=False,
        label="Status Notes (will be included in email)"
    )
    
    class Meta:
        model = Application
        fields = ['status']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget.attrs['class'] = 'form-select'

class SimpleInterviewForm(forms.ModelForm):
    """Simple form for scheduling interview - date, time, location only"""
    
    # Add email notification option
    send_email = forms.BooleanField(
        initial=True,
        required=False,
        label="Send interview invitation via email",
        help_text="Applicant will receive email with interview details"
    )
    
    additional_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Additional instructions for the applicant...'
        }),
        required=False,
        label="Additional Instructions"
    )
    
    class Meta:
        model = Interview
        fields = ['interview_date', 'interview_time', 'location']
        widgets = {
            'interview_date': forms.DateInput(attrs={'type': 'date'}),
            'interview_time': forms.TimeInput(attrs={'type': 'time'}),
            'location': forms.TextInput(attrs={'placeholder': 'Enter interview location/venue'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set minimum date to tomorrow
        tomorrow = timezone.now().date() + datetime.timedelta(days=1)
        self.fields['interview_date'].widget.attrs['min'] = tomorrow
    
    def clean_interview_date(self):
        """Validate interview date"""
        interview_date = self.cleaned_data['interview_date']
        today = timezone.now().date()
        
        if interview_date < today:
            raise forms.ValidationError("Interview date cannot be in the past.")
        
        return interview_date
    
    def clean_location(self):
        """Validate location"""
        location = self.cleaned_data.get('location', '').strip()
        if not location:
            raise forms.ValidationError("Please specify the interview location.")
        return location