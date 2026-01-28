from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from users.views import EmployerRequiredMixin
from .models import Company
from .forms import CompanyForm
from django.db.models import Q

class CompanyCreateView(EmployerRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'companies/company_form.html'
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def form_valid(self, form):
        form.instance.employer = self.request.user
        messages.success(self.request, 'Company profile created successfully!')
        return super().form_valid(form)
    
    def get(self, request, *args, **kwargs):
        # Check if company already exists
        if Company.objects.filter(employer=request.user).exists():
            messages.info(request, 'You already have a company profile.')
            return redirect('company_update')
        return super().get(request, *args, **kwargs)

class CompanyUpdateView(EmployerRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'companies/company_form.html'
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def get_object(self, queryset=None):
        # Try to get user's company
        try:
            return Company.objects.get(employer=self.request.user)
        except Company.DoesNotExist:
            # If no company, redirect will happen in dispatch
            return None
    
    def dispatch(self, request, *args, **kwargs):
        # First, try to get the object
        obj = self.get_object()
        if obj is None:
            messages.warning(request, 'Please create a company profile first.')
            return redirect('company_create')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, 'Company profile updated successfully!')
        return super().form_valid(form)

class CompanyDetailView(DetailView):
    model = Company
    template_name = 'companies/company_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_jobs'] = self.object.jobs.filter(is_active=True)
        return context

class CompanyListView(ListView):
    model = Company
    template_name = 'companies/company_list.html'
    paginate_by = 20
    context_object_name = 'companies'
    
    def get_queryset(self):
        # FIXED: LAHAT NG COMPANIES, KAHIT DI VERIFIED
        queryset = Company.objects.all()
        
        # Filter by industry
        industry = self.request.GET.get('industry')
        if industry:
            queryset = queryset.filter(industry=industry)
        
        # Filter by search query
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add search query to context
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_industry'] = self.request.GET.get('industry', '')
        
        # FIXED: Get industry counts for ALL companies
        industry_counts = {}
        all_companies = Company.objects.all()
        
        for company in all_companies:
            if company.industry:
                industry_counts[company.industry] = industry_counts.get(company.industry, 0) + 1
        
        context['industry_counts'] = industry_counts
        
        # Pass industry choices for dropdown
        context['industry_choices'] = Company.INDUSTRY_CHOICES
        
        return context