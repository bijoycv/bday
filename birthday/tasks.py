"""
Celery tasks for birthday wishes application.
"""
import pytz
from datetime import datetime
from celery import shared_task
from django.core.mail import EmailMessage
from django.utils import timezone


@shared_task
def send_scheduled_wishes_task():
    """
    Task to process and send all pending scheduled wishes.
    This runs periodically via Celery Beat.
    """
    from birthday.models import ScheduledWish, PatientStatus
    
    # Get California timezone
    ca_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(ca_tz)
    
    print(f'[{now.strftime("%Y-%m-%d %H:%M:%S %Z")}] Starting scheduled wishes processing...')
    
    # Get all pending wishes whose scheduled time has passed
    pending_wishes = ScheduledWish.objects.filter(
        status='Pending',
        scheduled_for__lte=now
    )
    
    total = pending_wishes.count()
    if total == 0:
        print('No pending wishes to send at this time.')
        return {'sent': 0, 'failed': 0, 'total': 0}
    
    print(f'Found {total} wish(es) to process.')
    
    sent_count = 0
    failed_count = 0
    
    for wish in pending_wishes:
        patient = wish.patient
        template = wish.template
        
        if not patient.email:
            wish.status = 'Failed'
            wish.error_message = 'Patient has no email address'
            wish.save()
            failed_count += 1
            print(f'  ✗ {patient}: No email address')
            continue
        
        if not template:
            wish.status = 'Failed'
            wish.error_message = 'No template associated with this wish'
            wish.save()
            failed_count += 1
            print(f'  ✗ {patient}: No template')
            continue
        
        try:
            # Prepare email content
            subject = wish.custom_subject or (template.subject if template else 'Happy Birthday!')
            body = wish.custom_body or (template.body if template else '')
            
            # Replace placeholders
            subject = subject.replace('{first_name}', patient.first_name)
            subject = subject.replace('{last_name}', patient.last_name)
            body = body.replace('{first_name}', patient.first_name)
            body = body.replace('{last_name}', patient.last_name)
            
            # Check if body is already HTML
            if '<p>' in body or '<br>' in body or '<div>' in body:
                html_body = body
                html_body = html_body.replace('<p>', '<p style="margin:0;padding:0;">')
            else:
                html_body = body.replace('\n', '<br>')
            
            # Add signature if available
            if template.signature:
                fixed_signature = template.signature.content.replace('<p>', '<p style="margin:0;padding:0;">')
                html_body += '<br>' + fixed_signature
            
            # Parse CC/BCC
            cc_list = [e.strip() for e in (wish.cc_recipients or '').split(',') if e.strip()]
            bcc_list = [e.strip() for e in (wish.bcc_recipients or '').split(',') if e.strip()]
            
            # Send email
            email = EmailMessage(
                subject=subject,
                body=html_body,
                from_email=None,
                to=[patient.email],
                cc=cc_list,
                bcc=bcc_list,
            )
            email.content_subtype = 'html'
            email.send(fail_silently=False)
            
            # Update wish status
            wish.status = 'Sent'
            wish.sent_at = timezone.now()
            wish.save()
            
            # Log activity
            PatientStatus.objects.create(
                patient=patient,
                activity_type='Email Sent',
                description=f'Scheduled Birthday Wish: {subject}',
                full_content=body
            )
            
            sent_count += 1
            print(f'  ✓ {patient}: Email sent successfully')
            
        except Exception as e:
            wish.status = 'Failed'
            wish.error_message = str(e)
            wish.save()
            failed_count += 1
            print(f'  ✗ {patient}: {str(e)}')
    
    print(f'Processing complete! Sent: {sent_count}, Failed: {failed_count}, Total: {total}')
    return {'sent': sent_count, 'failed': failed_count, 'total': total}
