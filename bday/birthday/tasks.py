"""
Celery tasks for birthday wishes application.
"""
import pytz
import os
from datetime import datetime
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from email.utils import formataddr
from .reports import send_daily_summary_report


@shared_task
def send_scheduled_wishes_task():
    """
    Task to process and send all pending scheduled wishes.
    This runs periodically via Celery Beat.
    """
    from birthday.models import ScheduledWish, PatientStatus, CommunicationLog
    
    # Get California timezone
    ca_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(ca_tz)
    
    print(f'[{now.strftime("%Y-%m-%d %H:%M:%S %Z")}] Starting scheduled wishes processing... (v1.1.0)')
    
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
    processed_patient_ids = []
    
    for wish in pending_wishes:
        patient = wish.patient
        processed_patient_ids.append(patient.id)
        
        # Check if patient accepts communications
        if not patient.accepts_marketing:
            wish.status = 'Failed'
            wish.error_message = f'Patient opted out. Reason: {patient.unsubscribe_reason}'
            wish.save()
            failed_count += 1
            continue

        template = wish.template
        if not template:
            wish.status = 'Failed'
            wish.error_message = 'Missing template'
            wish.save()
            failed_count += 1
            continue

        # --- ROUTING ENGINE v1.1.0 ---
        # We strictly honor the wish.channel field.
        channel = str(getattr(wish, 'channel', 'Email')).strip()
        
        # Print to terminal with high visibility
        print("="*60)
        print(f"CORE ENGINE v1.1.0: PROCESSING WISH #{wish.id}")
        print(f"CHANNEL: {channel} | PATIENT: {patient.first_name} {patient.last_name}")
        print("="*60)

        try:
            subject = wish.custom_subject or (template.subject if template else 'Happy Birthday!')
            body = wish.custom_body or (template.body if template else '')
            
            # Placeholder replacement
            subject = subject.replace('{first_name}', patient.first_name).replace('{last_name}', patient.last_name)
            body = body.replace('{first_name}', patient.first_name).replace('{last_name}', patient.last_name)

            if channel == 'SMS':
                print(f"ACTION [v1.1.0]: ROUTING TO TWILIO SMS ENGINE")
                if not patient.phone:
                    raise ValueError("Patient missing phone number for SMS")

                # Send SMS Logic
                from birthday.utils import send_sms
                import re, html
                
                # HTML to Text conversion
                text_content = body.replace('</p>', '\n\n').replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n').replace('</div>', '\n')
                clean_body = html.unescape(re.sub('<[^<]+?>', '', text_content))
                clean_body = re.sub(r'\n{3,}', '\n\n', clean_body).strip()
                
                success, result = send_sms(patient.phone, clean_body)
                
                if success:
                    wish.status = 'Sent'
                    wish.sent_at = timezone.now()
                    wish.save()
                    
                    PatientStatus.objects.create(
                        patient=patient,
                        activity_type='SMS Sent',
                        description=f'Scheduled Birthday SMS sent',
                        full_content=clean_body
                    )
                    CommunicationLog.objects.create(
                        patient=patient,
                        channel='SMS',
                        direction='Outbound',
                        status='Sent',
                        body=clean_body,
                        recipient=patient.phone,
                        external_message_id=result,
                        gateway_number=getattr(settings, 'TWILIO_PHONE_NUMBER', None) or os.getenv('TWILIO_PHONE_NUMBER'),
                        sent_at=timezone.now()
                    )
                    sent_count += 1
                    print(f"RESULT: SMS SUCCESS (SID: {result})")
                else:
                    raise Exception(f"Twilio Error: {result}")
            
            elif channel == 'Email':
                print(f"ACTION [v1.1.0]: ROUTING TO DJANGO EMAIL ENGINE")
                if not patient.email:
                    raise ValueError("Patient missing email address")

                # HTML Email Logic
                from django.core.mail import EmailMessage
                html_body = body
                if '<p>' in html_body or '<br>' in html_body:
                    html_body = html_body.replace('<p>', '<p style="margin:0;padding:0;">')
                else:
                    html_body = html_body.replace('\n', '<br>')
                
                # Signature is already baked into custom_body in views.py
                # This prevents double signatures.
                
                cc_list = [e.strip() for e in (wish.cc_recipients or '').split(',') if e.strip()]
                bcc_list = [e.strip() for e in (wish.bcc_recipients or '').split(',') if e.strip()]
                
                email = EmailMessage(
                    subject=subject,
                    body=html_body,
                    from_email=formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
                    to=[patient.email],
                    cc=cc_list,
                    bcc=bcc_list,
                )
                email.content_subtype = 'html'
                email.send(fail_silently=False)
                
                wish.status = 'Sent'
                wish.sent_at = timezone.now()
                wish.save()
                
                PatientStatus.objects.create(
                    patient=patient,
                    activity_type='Email Sent',
                    description=f'Scheduled Birthday Wish: {subject}',
                    full_content=body
                )
                CommunicationLog.objects.create(
                    patient=patient,
                    channel='Email',
                    direction='Outbound',
                    status='Sent',
                    subject=subject,
                    body=html_body,
                    recipient=patient.email,
                    sent_at=timezone.now()
                )
                sent_count += 1
                print("RESULT: EMAIL SUCCESS")
            
            else:
                raise ValueError(f"Unknown channel detected: {channel}")

        except Exception as e:
            error_msg = str(e)
            print(f"CRITICAL ERROR [v1.1.0]: {error_msg}")
            wish.status = 'Failed'
            wish.error_message = error_msg
            wish.save()
            if channel == 'SMS':
                CommunicationLog.objects.create(
                    patient=patient,
                    channel='SMS',
                    direction='Outbound',
                    status='Failed',
                    body=wish.custom_body or (wish.template.body if wish.template else ''),
                    recipient=patient.phone or '',
                    error_message=error_msg,
                    gateway_number=getattr(settings, 'TWILIO_PHONE_NUMBER', None) or os.getenv('TWILIO_PHONE_NUMBER')
                )
            failed_count += 1
    
    print(f'Done processing {total} wishes. Sent: {sent_count}, Failed: {failed_count}')
    
    # Trigger the CEO summary report immediately for the patients just processed
    if total > 0:
        print(f'Triggering activity report for {len(processed_patient_ids)} patients...')
        send_daily_summary_report(patient_ids=processed_patient_ids)
        
    return {'sent': sent_count, 'failed': failed_count, 'total': total}
