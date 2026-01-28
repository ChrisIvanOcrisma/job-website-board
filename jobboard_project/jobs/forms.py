from django import forms
from django.db.models import Q
from .models import Job, JobAlert, ScreeningQuestion, JobCategory, JobTag
from django.utils import timezone

class JobForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Python, Django, React, Remote...'
        }),
        help_text='Separate tags with commas'
    )
    
    # Education level field
    education_level = forms.ChoiceField(
        choices=[('', 'Select Education Level')] + list(Job.EDUCATION_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Experience years field
    experience_years = forms.ChoiceField(
        choices=[(None, 'Select Experience Required')] + list(Job.EXPERIENCE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Qualifications field
    qualifications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List specific qualifications required...'
        })
    )
    
    # Skills field
    skills = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Python, Django, JavaScript, SQL...'
        }),
        help_text='Separate skills with commas'
    )
    
    # Benefits field
    benefits = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Health insurance, Paid time off, Remote work...'
        })
    )
    
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'requirements',
            'location', 'is_remote', 'employment_type', 'category',
            'salary_min', 'salary_max', 'salary_currency',
            'application_email', 'application_url', 'deadline',
            'is_active', 'is_featured'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'is_remote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30000'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 80000'}),
            # FIXED: Salary currency with PHP as default and proper choices
            'salary_currency': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('PHP', 'Philippine Peso (PHP)'),
                ('USD', 'US Dollar ($)'),
                ('EUR', 'Euro (€)'),
                ('GBP', 'British Pound (£)'),
                ('JPY', 'Japanese Yen (¥)'),
            ]),
            'application_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'apply@company.com'}),
            'application_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://company.com/apply'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for custom fields
        if self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(
                [tag.name for tag in self.instance.tags.all()]
            )
            # Set initial values for our custom fields
            self.fields['education_level'].initial = self.instance.education_level
            self.fields['experience_years'].initial = self.instance.experience_years
            self.fields['qualifications'].initial = self.instance.qualifications
            self.fields['skills'].initial = self.instance.skills
            self.fields['benefits'].initial = self.instance.benefits
        
        # Set field labels and help texts
        self.fields['benefits'].label = "Benefits & Perks"
        self.fields['qualifications'].label = "Required Qualifications"
        self.fields['skills'].label = "Required Skills"
        self.fields['education_level'].label = "Minimum Education"
        self.fields['experience_years'].label = "Years of Experience"
        
        # Set default value for salary_currency to PHP if not set
        if not self.instance.pk or not self.instance.salary_currency:
            self.fields['salary_currency'].initial = 'PHP'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate salary range
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise forms.ValidationError({
                'salary_min': 'Minimum salary cannot be greater than maximum salary.'
            })
        
        # Validate deadline
        deadline = cleaned_data.get('deadline')
        if deadline and deadline < timezone.now().date():
            raise forms.ValidationError({
                'deadline': 'Deadline cannot be in the past.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        job = super().save(commit=False)
        
        # Handle the custom form fields
        job.education_level = self.cleaned_data.get('education_level') or None
        job.experience_years = self.cleaned_data.get('experience_years') or 0
        job.qualifications = self.cleaned_data.get('qualifications') or ''
        job.skills = self.cleaned_data.get('skills') or ''
        job.benefits = self.cleaned_data.get('benefits') or ''
        
        # Ensure salary_currency has a value
        if not job.salary_currency:
            job.salary_currency = 'PHP'
        
        if commit:
            job.save()
            # Save tags
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                job.tags.clear()
                for tag_name in tags:
                    tag, created = JobTag.objects.get_or_create(
                        name=tag_name,
                        defaults={'slug': tag_name.lower().replace(' ', '-')}
                    )
                    job.tags.add(tag)
            else:
                job.tags.clear()
        
        return job

class JobFilterForm(forms.Form):
    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job title, skills, or company'
        })
    )
    
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City, state, or remote'
        })
    )
    
    remote = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any Location'),
            ('remote', 'Remote Only'),
            ('onsite', 'On-site Only')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=JobCategory.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    education_level = forms.ChoiceField(
        choices=[('', 'Any Education Level')] + list(Job.EDUCATION_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    experience_years = forms.ChoiceField(
        choices=[('', 'Any Experience')] + list(Job.EXPERIENCE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    employment_type = forms.ChoiceField(
        choices=[('', 'Any Type')] + list(Job.EMPLOYMENT_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = JobCategory.objects.all().order_by('name')

class JobAlertForm(forms.ModelForm):
    # Alert name field
    name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Python Developer Alerts'
        }),
        help_text='Give your alert a descriptive name'
    )
    
    # Frequency field - FIXED: Use JobAlert's FREQUENCY_CHOICES
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('INSTANT', 'Instant'),
    ]
    frequency = forms.ChoiceField(
        choices=FREQUENCY_CHOICES,
        initial='DAILY',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Employment type field
    employment_type = forms.ChoiceField(
        choices=[('', 'Any Type')] + list(Job.EMPLOYMENT_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Salary fields
    min_salary = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 30000'
        })
    )
    
    max_salary = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 80000'
        })
    )
    
    # Education level field
    education_level = forms.ChoiceField(
        choices=[('', 'Any Education Level')] + list(Job.EDUCATION_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Experience years field
    experience_years = forms.ChoiceField(
        choices=[('', 'Any Experience')] + [(str(k), v) for k, v in Job.EXPERIENCE_CHOICES],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Remote work field
    is_remote = forms.ChoiceField(
        choices=[
            ('', 'Any'),
            ('true', 'Remote Only'),
            ('false', 'On-site Only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = JobAlert
        fields = [
            'name', 'keyword', 'location', 'category', 
            'is_remote', 'email_notifications', 'is_active'
        ]
        widgets = {
            'keyword': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python Developer'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Manila or Remote'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make fields optional
        self.fields['name'].required = False
        self.fields['keyword'].required = False
        self.fields['location'].required = False
        self.fields['category'].required = False
        self.fields['employment_type'].required = False
        self.fields['min_salary'].required = False
        self.fields['max_salary'].required = False
        self.fields['education_level'].required = False
        self.fields['experience_years'].required = False
        
        # Set initial values if editing
        if self.instance and self.instance.pk:
            # Set initial for is_remote
            if self.instance.is_remote is not None:
                self.fields['is_remote'].initial = 'true' if self.instance.is_remote else 'false'
            
            # Set initial for frequency if it exists
            if hasattr(self.instance, 'frequency'):
                self.fields['frequency'].initial = self.instance.frequency
            
            # Set initial for employment_type if it exists
            if self.instance.employment_type:
                self.fields['employment_type'].initial = self.instance.employment_type
            
            # Set initial for salary fields if they exist
            if self.instance.min_salary:
                self.fields['min_salary'].initial = self.instance.min_salary
            if self.instance.max_salary:
                self.fields['max_salary'].initial = self.instance.max_salary
            
            # Set initial for education_level if it exists
            if self.instance.education_level:
                self.fields['education_level'].initial = self.instance.education_level
            
            # Set initial for experience_years if it exists
            if self.instance.experience_years is not None:
                self.fields['experience_years'].initial = str(self.instance.experience_years)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate salary range
        min_salary = cleaned_data.get('min_salary')
        max_salary = cleaned_data.get('max_salary')
        
        if min_salary and max_salary and min_salary > max_salary:
            raise forms.ValidationError({
                'min_salary': 'Minimum salary cannot be greater than maximum salary.'
            })
        
        # Auto-generate name if empty
        if not cleaned_data.get('name'):
            parts = []
            if cleaned_data.get('keyword'):
                parts.append(cleaned_data.get('keyword'))
            if cleaned_data.get('location'):
                parts.append(f"in {cleaned_data.get('location')}")
            if cleaned_data.get('category'):
                category = cleaned_data.get('category')
                parts.append(f"({category.name if hasattr(category, 'name') else category})")
            
            cleaned_data['name'] = " ".join(parts) if parts else "My Job Alert"
        
        return cleaned_data
    
    def save(self, commit=True):
        alert = super().save(commit=False)
        
        if self.user:
            alert.job_seeker = self.user
        
        # Handle is_remote field
        is_remote = self.cleaned_data.get('is_remote')
        if is_remote == 'true':
            alert.is_remote = True
        elif is_remote == 'false':
            alert.is_remote = False
        else:
            alert.is_remote = None
        
        # Set the additional fields
        alert.frequency = self.cleaned_data.get('frequency', 'DAILY')
        alert.employment_type = self.cleaned_data.get('employment_type') or None
        alert.min_salary = self.cleaned_data.get('min_salary') or None
        alert.max_salary = self.cleaned_data.get('max_salary') or None
        alert.education_level = self.cleaned_data.get('education_level') or None
        
        # Handle experience_years - convert string back to integer
        experience_years = self.cleaned_data.get('experience_years')
        if experience_years:
            try:
                alert.experience_years = int(experience_years)
            except (ValueError, TypeError):
                alert.experience_years = None
        else:
            alert.experience_years = None
        
        if commit:
            alert.save()
        
        return alert

class ScreeningQuestionForm(forms.ModelForm):
    class Meta:
        model = ScreeningQuestion
        fields = ['question', 'question_type', 'is_required', 'order']
        widgets = {
            'question': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter screening question...'
            }),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }