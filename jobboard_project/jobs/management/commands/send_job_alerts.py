# jobs/management/commands/send_scheduled_alerts.py
from django.core.management.base import BaseCommand
from jobs.models import JobAlert

class Command(BaseCommand):
    help = 'Send scheduled job alerts (daily/weekly)'
    
    def handle(self, *args, **options):
        alerts = JobAlert.objects.filter(
            email_notifications=True,
            is_active=True,
            frequency__in=['DAILY', 'WEEKLY']
        )
        
        sent_count = 0
        
        for alert in alerts:
            if alert.should_send_scheduled_email():
                jobs_sent = alert.send_email_notification()
                if jobs_sent > 0:
                    sent_count += 1
                    self.stdout.write(f"✅ Sent {alert.frequency.lower()} alert")
        
        self.stdout.write(f"🎉 Sent {sent_count} scheduled alerts")