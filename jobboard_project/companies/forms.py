from django import forms
from .models import Company

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'description', 'website', 'location', 
            'address', 'logo', 'industry', 'size', 'founded_year'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
            # ADD INDUSTRY WIDGET
            'industry': forms.Select(attrs={'class': 'form-select'}),
            'founded_year': forms.NumberInput(attrs={
                'min': 1800,
                'max': 2025,
                'placeholder': 'e.g., 2010'
            }),
            'size': forms.TextInput(attrs={
                'placeholder': 'e.g., 1-10 employees, 11-50 employees, 51-200 employees'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set industry as required
        self.fields['industry'].required = True
        
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field_name != 'industry':  # industry already has form-select
                field.widget.attrs['class'] = 'form-control'
        
        # Special handling for specific fields
        self.fields['logo'].widget.attrs['class'] = 'form-control-file'
        
        # Make optional fields
        self.fields['website'].required = False
        self.fields['logo'].required = False
        self.fields['founded_year'].required = False
        self.fields['size'].required = False
        
        # Set industry choices from model
        self.fields['industry'].choices = [
            ('', 'Select Industry')  # Empty option
        ] + Company.INDUSTRY_CHOICES
        
        # Add help text
        self.fields['industry'].help_text = 'Select your company primary industry'