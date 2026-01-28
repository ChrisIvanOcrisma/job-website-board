class RoleRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check BEFORE processing the request
        if request.user.is_authenticated:
            # Check if employer needs to create company
            if (request.user.is_employer() and 
                not request.path.startswith('/companies/') and  # FIXED: '/company/' to '/companies/'
                not request.path.startswith('/admin/') and
                not request.path.startswith('/logout/')):
                
                from companies.models import Company
                try:
                    Company.objects.get(employer=request.user)
                except Company.DoesNotExist:
                    from django.shortcuts import redirect
                    return redirect('company_create')  # This causes INFINITE LOOP!
        
        response = self.get_response(request)
        return response