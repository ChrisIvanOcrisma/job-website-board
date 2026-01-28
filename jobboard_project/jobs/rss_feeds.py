from django.contrib.syndication.views import Feed
from django.urls import reverse_lazy
from .models import Job

class LatestJobsFeed(Feed):
    title = "Latest Jobs on JobBoard"
    link = reverse_lazy("job_list")
    description = "Latest job postings on our platform"
    
    def items(self):
        return Job.objects.filter(is_active=True).order_by('-created_at')[:50]
    
    def item_title(self, item):
        return item.title
    
    def item_description(self, item):
        return f"{item.company.name} - {item.location}\n\n{item.description[:200]}..."
    
    def item_link(self, item):
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        return item.created_at