import django_filters
from django.db.models import Q
from .models import Job, JobCategory

class JobFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(
        method='filter_by_keyword',
        label='Search'
    )
    location = django_filters.CharFilter(
        field_name='location',
        lookup_expr='icontains',
        label='Location'
    )
    salary_min = django_filters.NumberFilter(
        field_name='salary_min',
        lookup_expr='gte',
        label='Minimum Salary'
    )
    salary_max = django_filters.NumberFilter(
        field_name='salary_max',
        lookup_expr='lte',
        label='Maximum Salary'
    )
    is_remote = django_filters.BooleanFilter(
        field_name='is_remote',
        label='Remote Only'
    )
    employment_type = django_filters.MultipleChoiceFilter(
        field_name='employment_type',
        choices=Job.EMPLOYMENT_TYPE_CHOICES,
        label='Employment Type'
    )
    category = django_filters.ModelChoiceFilter(
        field_name='category',
        queryset=JobCategory.objects.all(),
        label='Category'
    )
    
    class Meta:
        model = Job
        fields = ['keyword', 'location', 'salary_min', 'salary_max', 
                 'is_remote', 'employment_type', 'category']
    
    def filter_by_keyword(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(title__icontains=value) |
                Q(description__icontains=value) |
                Q(requirements__icontains=value) |
                Q(company__name__icontains=value)
            )
        return queryset