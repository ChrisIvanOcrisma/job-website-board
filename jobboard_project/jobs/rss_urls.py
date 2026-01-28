from django.urls import path
from .rss_feeds import LatestJobsFeed

urlpatterns = [
    path('jobs/', LatestJobsFeed(), name='job_feed'),
]