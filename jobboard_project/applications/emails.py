# applications/emails.py
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta

def convert_to_12h_format(time_24h):
    """Convert 24-hour time to 12-hour format (01:00 PM, 02:30 PM, etc.)"""
    if not time_24h:
        return ""
    
    time_str = str(time_24h)
    
    try:
        if ':' in time_24h:
            parts = time_24h.split(':')
            hour = int(parts[0])
            minute = parts[1]
            
            # Remove seconds if present (14:30:00 → 14:30)
            if len(parts) > 2:
                minute = minute[:2]
            
            # Ensure minute has 2 digits
            if len(minute) == 1:
                minute = f"0{minute}"
            
            # Convert to 12-hour format
            if hour == 0:
                return f"12:{minute} AM"
            elif hour == 12:
                return f"12:{minute} PM"
            elif hour > 12:
                return f"{hour-12:02d}:{minute} PM"  # 13 → 01, 14 → 02
            else:
                return f"{hour:02d}:{minute} AM"  # 9 → 09, 11 → 11
    except Exception as e:
        print(f"Error converting time {time_24h}: {e}")
    
    return time_str

def get_next_monday():
    """Calculate the next Monday from today"""
    today = datetime.now().date()
    days_ahead = 0 - today.weekday()  # Monday is 0
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def send_application_status_email(application, old_status=None):
    """
    Send email when application status changes
    """
    if not application.email:
        print(f"No email for application {application.id}")
        return False
    
    # Get company name and address
    company_name = "the company"
    company_address = ""
    
    if hasattr(application.job, 'company'):
        company = application.job.company
        if hasattr(company, 'name'):
            company_name = company.name
        
        # Get company address
        if hasattr(company, 'address'):
            company_address = company.address
        elif hasattr(company, 'location'):
            company_address = company.location
    
    # Email content based on status
    status_messages = {
        'PENDING': {
            'subject': f'Application Received: {application.job.title}',
            'message': f"""Dear {application.full_name},

Thank you for applying for the {application.job.title} position at {company_name}.

This email confirms that we have received your application. Our hiring team will review your qualifications and contact you if your profile matches our requirements.

Application Details:
- Position: {application.job.title}
- Company: {company_name}
- Date Applied: {application.applied_at.strftime('%B %d, %Y')}

You can check your application status at any time by logging into your account.

Sincerely,
The Recruitment Team
{company_name}
"""
        },
        'REVIEWED': {
            'subject': f'Application Under Review: {application.job.title}',
            'message': f"""Dear {application.full_name},

Your application for the {application.job.title} position at {company_name} is now under review.

Our hiring team is carefully evaluating your qualifications against the position requirements. We will notify you of any updates regarding your application status.

Current Status: Under Review

Thank you for your interest in {company_name}.

Sincerely,
The Recruitment Team
{company_name}
"""
        },
        'SHORTLISTED': {
            'subject': f'Application Shortlisted: {application.job.title}',
            'message': f"""Dear {application.full_name},

We are pleased to inform you that your application for the {application.job.title} position at {company_name} has been shortlisted.

Your qualifications have impressed our hiring team, and you have been selected to proceed to the next stage of the selection process. We will contact you shortly with further details regarding the next steps.

Congratulations on this achievement.

Sincerely,
The Recruitment Team
{company_name}
"""
        },
        'INTERVIEW': {
            'subject': f'Interview Scheduled: {application.job.title}',
            'message': f"""Dear {application.full_name},

Your application for the {application.job.title} position at {company_name} has progressed to the interview stage.

An interview has been scheduled for you. Please check your application dashboard for the complete interview details including date, time, and location.

We look forward to meeting with you.

Sincerely,
The Recruitment Team
{company_name}
"""
        },
        'OFFER': {
            'subject': f'Job Offer: {application.job.title}',
            'message': f"""Dear {application.full_name},

We are pleased to extend a job offer for the {application.job.title} position at {company_name}.

Please log in to your application dashboard to review the offer details and next steps.

We look forward to welcoming you to our team.

Sincerely,
The Recruitment Team
{company_name}
"""
        },
        'HIRED': {
            'subject': f'Congratulations! Hired for {application.job.title}',
            'message': f"""Dear {application.full_name},

Congratulations! We are pleased to inform you that you have been hired for the {application.job.title} position at {company_name}.

Start Details:
Date: Monday, {get_next_monday().strftime('%B %d, %Y')}
Time: 8:00 AM
Location: {company_address or company_name} - HR Department

Please proceed to the HR Department on the ground floor upon arrival.

We are excited to have you join our team and look forward to working with you.

Welcome to {company_name}!

Sincerely,
The Human Resources Department
{company_name}
"""
        },
        'REJECTED': {
            'subject': f'Update on Your Application: {application.job.title}',
            'message': f"""Dear {application.full_name},

Thank you for applying for the {application.job.title} position at {company_name} and for the time you invested in our selection process.

After careful consideration, we regret to inform you that we have decided to proceed with other candidates whose qualifications more closely match our current requirements.

We appreciate your interest in {company_name} and encourage you to apply for future opportunities that align with your skills and experience.

We wish you success in your job search.

Sincerely,
The Recruitment Team
{company_name}
"""
        },
        'WITHDRAWN': {
            'subject': f'Application Withdrawn: {application.job.title}',
            'message': f"""Dear {application.full_name},

This email confirms that your application for the {application.job.title} position at {company_name} has been withdrawn.

If this action was taken in error or if you wish to reapply, please contact our recruitment team.

Thank you for your interest in {company_name}.

Sincerely,
The Recruitment Team
{company_name}
"""
        }
    }
    
    # Get email content based on status
    email_content = status_messages.get(application.status, {
        'subject': f'Application Status Update: {application.job.title}',
        'message': f"""Dear {application.full_name},

This email is to inform you that your application status has been updated to: {application.get_status_display()}

Please log in to your account for more details.

Sincerely,
The Recruitment Team
{company_name}
"""
    })
    
    print(f"Preparing to send email to: {application.email}")
    print(f"Status: {application.status}")
    
    try:
        send_mail(
            subject=email_content['subject'],
            message=email_content['message'],
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=False,
        )
        print(f"Email sent to {application.email} for status: {application.status}")
        return True
    except Exception as e:
        print(f"Error sending email to {application.email}: {e}")
        return False

def send_hired_details_email(application):
    """
    Send formal hired email with start date, time, and location
    """
    if not application.email:
        print(f"No email for hired application {application.id}")
        return False
    
    # Get company name and address
    company_name = "the company"
    company_address = ""
    
    if hasattr(application.job, 'company'):
        company = application.job.company
        if hasattr(company, 'name'):
            company_name = company.name
        
        # Get company address
        if hasattr(company, 'address'):
            company_address = company.address
        elif hasattr(company, 'location'):
            company_address = company.location
    
    # Always calculate next Monday
    start_date = get_next_monday()
    start_date_display = f"Monday, {start_date.strftime('%B %d, %Y')}"
    
    subject = f'Welcome to {company_name}! Start Details for {application.job.title}'
    
    message = f"""Dear {application.full_name},

Congratulations on being hired for the {application.job.title} position at {company_name}!

We are delighted to welcome you to our team. Please find your start details below:

Start Date: {start_date_display}
Start Time: 8:00 AM
Location: {company_address or company_name} - HR Department

Upon arrival, please proceed directly to the HR Department on the ground floor. Our HR representative will assist you with the onboarding process.

Please bring the following documents:
1. Original government-issued IDs
2. Original educational certificates and transcripts
3. Two (2) recent 2x2 ID photos
4. Bank account details for payroll setup

If you have any questions before your start date, please do not hesitate to contact us.

We look forward to having you join our team and contribute to our success.

Welcome aboard!

Sincerely,
The Human Resources Department
{company_name}
"""
    
    print(f"Preparing hired email to: {application.email}")
    print(f"Start date: {start_date_display}")
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=False,
        )
        print(f"Hired email sent to {application.email}")
        return True
    except Exception as e:
        print(f"Error sending hired email to {application.email}: {e}")
        return False

def send_simple_interview_email(interview):
    """
    Send professional interview invitation email
    """
    application = interview.application
    
    # Get company name
    company_name = "the company"
    if hasattr(application.job, 'company'):
        if hasattr(application.job.company, 'name'):
            company_name = application.job.company.name
    
    # Convert time to 12-hour format
    time_12h = convert_to_12h_format(interview.interview_time)
    
    subject = f'Interview Invitation: {application.job.title}'
    
    message = f"""Dear {application.full_name},

We are pleased to invite you for an interview for the {application.job.title} position at {company_name}.

Interview Details:
Date: {interview.interview_date}
Time: {time_12h}
Location: {interview.location}

Please arrive 10-15 minutes prior to your scheduled interview time. Bring an updated copy of your resume and any relevant supporting documents.

If you need to reschedule or have any questions, please contact us at your earliest convenience.

We look forward to meeting with you.

Sincerely,
The Recruitment Team
{company_name}
"""
    
    print(f"Preparing interview email to: {application.email}")
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=False,
        )
        print(f"Interview email sent to {application.email}")
        return True
    except Exception as e:
        print(f"Error sending interview email to {application.email}: {e}")
        return False

def send_interview_cancellation_email(interview, reason=""):
    """
    Send professional interview cancellation email
    """
    application = interview.application
    
    # Get company name
    company_name = "the company"
    if hasattr(application.job, 'company'):
        if hasattr(application.job.company, 'name'):
            company_name = application.job.company.name
    
    # Convert time to 12-hour format
    time_12h = convert_to_12h_format(interview.interview_time)
    
    subject = f'Interview Cancellation: {application.job.title}'
    
    message = f"""Dear {application.full_name},

We regret to inform you that your scheduled interview for the {application.job.title} position has been cancelled.

Cancelled Interview Details:
Position: {application.job.title}
Date: {interview.interview_date}
Time: {time_12h}

{f'Reason: {reason}' if reason else 'Due to unforeseen circumstances, we must cancel the scheduled interview.'}

We sincerely apologize for any inconvenience this may cause. Our recruitment team will contact you shortly regarding potential rescheduling options.

Thank you for your understanding.

Sincerely,
The Recruitment Team
{company_name}
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=False,
        )
        print(f"Interview cancellation email sent to {application.email}")
        return True
    except Exception as e:
        print(f"Error sending cancellation email to {application.email}: {e}")
        return False

def send_interview_reschedule_email(interview, new_date, new_time, new_location):
    """
    Send professional interview reschedule email
    """
    application = interview.application
    
    # Get company name
    company_name = "the company"
    if hasattr(application.job, 'company'):
        if hasattr(application.job.company, 'name'):
            company_name = application.job.company.name
    
    # Convert times to 12-hour format
    old_time_12h = convert_to_12h_format(interview.interview_time)
    new_time_12h = convert_to_12h_format(new_time)
    
    subject = f'Interview Rescheduled: {application.job.title}'
    
    message = f"""Dear {application.full_name},

This email is to inform you that your interview for the {application.job.title} position has been rescheduled.

Original Schedule:
Date: {interview.interview_date}
Time: {old_time_12h}
Location: {interview.location}

Updated Schedule:
Date: {new_date}
Time: {new_time_12h}
Location: {new_location}

We apologize for any inconvenience this change may cause and appreciate your flexibility. Please update your calendar with the new interview details.

If the new schedule presents any conflicts, please contact us as soon as possible.

We look forward to meeting with you.

Sincerely,
The Recruitment Team
{company_name}
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=False,
        )
        print(f"Interview reschedule email sent to {application.email}")
        return True
    except Exception as e:
        print(f"Error sending reschedule email to {application.email}: {e}")
        return False

def send_application_confirmation_email(application):
    """
    Send professional application confirmation email
    """
    # Get company name
    company_name = "the company"
    if hasattr(application.job, 'company'):
        if hasattr(application.job.company, 'name'):
            company_name = application.job.company.name
    
    subject = f'Application Confirmation: {application.job.title}'
    
    message = f"""Dear {application.full_name},

Thank you for submitting your application for the {application.job.title} position at {company_name}.

This email confirms that we have successfully received your application. Our recruitment team will review your qualifications and contact you if your profile matches our requirements.

Application Details:
Position: {application.job.title}
Date Submitted: {application.applied_at.strftime('%B %d, %Y')}
Application ID: {application.id}

You can check the status of your application at any time by logging into your account.

We appreciate your interest in joining our team.

Sincerely,
The Recruitment Team
{company_name}
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=False,
        )
        print(f"Application confirmation email sent to {application.email}")
        return True
    except Exception as e:
        print(f"Error sending confirmation email to {application.email}: {e}")
        return False

# For testing - print email to console instead of sending
def send_test_email(application, status):
    """
    Test function to print email content to console
    """
    print("\n" + "="*50)
    print(f"TEST EMAIL for: {application.email}")
    print(f"Status: {status}")
    print("="*50)
    
    # Get email content
    from .models import Application
    temp_app = application
    temp_app.status = status
    
    try:
        from .emails import send_application_status_email
        result = send_application_status_email(temp_app)
        print(f"Email sent: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("="*50 + "\n")

# Test the time conversion
def test_time_conversion():
    """Test function for time conversion"""
    test_times = [
        "13:00",    # 01:00 PM
        "13:30",    # 01:30 PM  
        "14:00",    # 02:00 PM
        "09:00",    # 09:00 AM
        "09:30",    # 09:30 AM
        "12:00",    # 12:00 PM
        "00:00",    # 12:00 AM
        "23:45",    # 11:45 PM
        "17:15",    # 05:15 PM
        "08:05",    # 08:05 AM
    ]
    
    print("Testing time conversion:")
    print("="*30)
    for time_24h in test_times:
        time_12h = convert_to_12h_format(time_24h)
        print(f"{time_24h} → {time_12h}")