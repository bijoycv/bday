from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from datetime import timedelta, datetime, date
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse
from django.conf import settings
from django.core.mail import get_connection, EmailMessage
from email.utils import formataddr

from .models import PatientStatus, ScheduledWish, Patient
from xhtml2pdf import pisa
import io
import os

def report_dashboard(request):
    """View to show the report selection page."""
    return render(request, 'birthday/reports/dashboard.html')


def daily_report_api_docs(request):
    """Human-readable API documentation page for the daily report endpoint."""
    api_path = reverse('daily_report_api')
    api_url = request.build_absolute_uri(api_path)

    context = {
        'api_url': api_url,
        'api_path': api_path,
        'docs_generated_at': timezone.now(),
        'sample_date': timezone.localdate().isoformat(),
    }
    return render(request, 'birthday/reports/api_docs.html', context)

def get_report_data(period='weekly'):
    """Helper function to calculate report data for a given period."""
    today = date.today()
    
    if period == 'weekly':
        # Calculate last Monday and last Sunday
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        start_date = this_monday - timedelta(days=7) # Last Monday
        end_date = start_date + timedelta(days=6)    # Last Sunday
        title = "Weekly Birthday Report (Last Week)"
    else:
        start_date = today - timedelta(days=30)
        end_date = today
        title = "Monthly Birthday Report"
    
    all_patients = Patient.objects.all()
    upcoming_list = []
    
    for p in all_patients:
        if not p.dob: continue
        
        # Determine birthday for this calendar year
        try:
            bday_this_year = date(today.year, p.dob.month, p.dob.day)
        except ValueError: # Leap year Feb 29
            bday_this_year = date(today.year, 3, 1)
            
        # If the range spans across a year boundary, we might need to check next year's bday too
        try:
            bday_next_year = date(today.year + 1, p.dob.month, p.dob.day)
        except ValueError:
            bday_next_year = date(today.year + 1, 3, 1)

        # Check if either birthday falls within start_date and end_date
        target_bday = None
        if start_date <= bday_this_year <= end_date:
            target_bday = bday_this_year
        elif start_date <= bday_next_year <= end_date:
            target_bday = bday_next_year
            
        if target_bday:
            p.bday_this_year = target_bday
            p.age_turning = target_bday.year - p.dob.year

            if p.patient_type == 'Proceed' and p.enrollment_date and p.enrollment_date >= today - timedelta(days=365):
                p.status_label = 'Active'
                p.status_class = 'success'
            elif p.patient_type == 'Proceed':
                p.status_label = 'Not Active'
                p.status_class = 'danger'
            else:
                p.status_label = 'Not Regd'
                p.status_class = 'warning'
            
            # Check for outreach from the start of the period up to now
            # This ensures manual markings today for past reports are captured
            p.email_done = PatientStatus.objects.filter(
                patient=p,
                activity_type='Email Sent',
                created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            ).exists()
            
            p.sms_done = PatientStatus.objects.filter(
                patient=p,
                activity_type='SMS Sent',
                created_at__gte=timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            ).exists()

            # Check for recent outreach (last 14 days) for the overall Status badge
            recent_activity = PatientStatus.objects.filter(
                patient=p,
                activity_type__in=['Email Sent', 'SMS Sent'],
                created_at__gte=timezone.now() - timedelta(days=14)
            ).order_by('-created_at').first()
            p.last_outreach = recent_activity
            upcoming_list.append(p)
            
    # Sort by the actual birthday date in the range
    upcoming_list.sort(key=lambda x: x.bday_this_year)
    
    # Summary stats based on the patients in this specific report
    total_birthdays = len(upcoming_list)
    email_outreach = sum(1 for p in upcoming_list if p.email_done)
    sms_outreach = sum(1 for p in upcoming_list if p.sms_done)

    proceed_active = [
        p for p in upcoming_list
        if p.patient_type == 'Proceed'
        and p.enrollment_date
        and p.enrollment_date >= today - timedelta(days=365)
    ]
    proceed_inactive = [
        p for p in upcoming_list
        if p.patient_type == 'Proceed'
        and (not p.enrollment_date or p.enrollment_date < today - timedelta(days=365))
    ]
    expiring_soon = [
        p for p in upcoming_list
        if p.patient_type == 'Proceed'
        and p.enrollment_date
        and today - timedelta(days=365) <= p.enrollment_date < today - timedelta(days=335)
    ]
    not_registered = [p for p in upcoming_list if p.patient_type != 'Proceed']

    return {
        'title': title,
        'period': period,
        'report_type': 'birthday',
        'start_date': start_date,
        'end_date': end_date,
        'patients': upcoming_list,
        'total_birthdays': total_birthdays,
        'email_sent': email_outreach,
        'sms_sent': sms_outreach,
        'proceed_active': proceed_active,
        'proceed_inactive': proceed_inactive,
        'expiring_soon': expiring_soon,
        'not_registered': not_registered,
        'generated_at': timezone.now(),
    }

def get_expiring_report_data(period='weekly'):
    """Helper function to calculate expiring plans for the next week/month."""
    today = date.today()
    if period == 'weekly':
        # Calculate next week (Monday to Sunday)
        # Weekday: 0=Mon, 1=Tue, ..., 6=Sun
        days_until_next_monday = 7 - today.weekday()
        start_date = today + timedelta(days=days_until_next_monday)
        end_date = start_date + timedelta(days=6)
        title = "Weekly Plan Expiration Report (Next Week)"
    else:
        start_date = today
        end_date = today + timedelta(days=30)
        title = "Monthly Plan Expiration Report (Next 30 Days)"

    # Plans enrolled ~1 year ago
    start_search = start_date - timedelta(days=365)
    end_search = end_date - timedelta(days=365)
    
    patients = Patient.objects.filter(
        patient_type='Proceed',
        enrollment_date__gte=start_search,
        enrollment_date__lte=end_search
    ).order_by('enrollment_date')
    
    # Enrich patients for template
    for p in patients:
        p.expiry_date = p.enrollment_date + timedelta(days=365)
        p.days_until_expiry = (p.expiry_date - today).days
        p.status_label = 'Expiring'
        p.status_class = 'warning'
        if p.days_until_expiry < 0:
            p.status_label = 'Expired'
            p.status_class = 'danger'

    return {
        'title': title,
        'period': period,
        'report_type': 'expiring',
        'start_date': start_date,
        'end_date': end_date,
        'patients': patients,
        'total_expiring': patients.count(),
        'generated_at': timezone.now(),
        'recipient_email': "bijoy@sivasolutions.com"
    }

def generate_report(request):
    """View to generate the report based on period and format."""
    period = request.GET.get('period', 'weekly')
    report_format = request.GET.get('format', 'html')
    report_type = request.GET.get('type', 'birthday')
    
    if report_type == 'expiring':
        context = get_expiring_report_data(period)
    else:
        context = get_report_data(period)
        context['report_type'] = 'birthday'
    
    context['recipient_email'] = "bijoy@sivasolutions.com"
    
    if report_format == 'pdf':
        template = 'birthday/reports/report_pdf.html' if report_type == 'birthday' else 'birthday/reports/expiring_report_pdf.html'
        html = render_to_string(template, context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{period}_{date.today().strftime("%Y%m%d")}.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('PDF generation error')
        return response
    
    return render(request, 'birthday/reports/report_view.html', context)

def get_report_email_connection():
    """
    Creates and returns an email connection using report-specific SMTP settings from .env.
    Falls back to default Django settings if a specific host is not provided.
    """
    host = os.getenv('REPORT_EMAIL_HOST')
    if not host:
        # If no specific report host, use the default connection from settings.
        # This will use EMAIL_BACKEND and its settings.
        return get_connection(fail_silently=False)

    port = int(os.getenv('REPORT_EMAIL_PORT', 587))
    use_tls = os.getenv('REPORT_EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    username = os.getenv('REPORT_EMAIL_HOST_USER')
    password = os.getenv('REPORT_EMAIL_HOST_PASSWORD')

    # When using a specific host, we assume SMTP backend.
    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=host,
        port=port,
        username=username,
        password=password,
        use_tls=use_tls,
        fail_silently=False,
    )
def send_report_email(period='weekly', report_type='birthday', recipient_list=None, cc_list=None, bcc_list=None):
    """Function to send the report as an HTML email."""
    if not recipient_list:
        admin_email = "bijoy@sivasolutions.com"
        recipient_list = [admin_email]
    
    if report_type == 'expiring':
        context = get_expiring_report_data(period)
        template = 'birthday/emails/expiring_report_email.html'
    else:
        context = get_report_data(period)
        template = 'birthday/emails/report_email.html'
    
    html_content = render_to_string(template, context)
    subject = f"{context['title']} - {context['generated_at'].strftime('%b %d, %Y')}"
    
    # Use report-specific settings, falling back to defaults
    report_from_name = os.getenv('REPORT_EMAIL_FROM_NAME', settings.EMAIL_FROM_NAME)
    report_from_email = os.getenv('REPORT_DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)
    connection = get_report_email_connection()

    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=formataddr((report_from_name, report_from_email)),
        to=recipient_list,
        cc=cc_list,
        bcc=bcc_list,
        connection=connection
    )
    email.content_subtype = "html"
    email.send()
    return True

def email_report_trigger(request):
    """View trigger to manually test the email report."""
    period = request.GET.get('period', 'weekly')
    report_type = request.GET.get('type', 'birthday')
    
    # Helper to parse multiple emails from comma-separated string
    def parse_emails(email_str):
        if not email_str:
            return []
        return [e.strip() for e in email_str.split(',') if e.strip()]

    recipients = parse_emails(request.GET.get('email', "bijoy@sivasolutions.com"))
    cc_list = parse_emails(request.GET.get('cc', ''))
    bcc_list = parse_emails(request.GET.get('bcc', ''))
    
    if not recipients:
        recipients = ["bijoy@sivasolutions.com"]

    success = send_report_email(period, report_type, recipients, cc_list, bcc_list)
    
    if success:
        recipient_display = ", ".join(recipients)
        return JsonResponse({'status': 'success', 'message': f'Report email sent to {recipient_display}'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to send report email'})

@require_POST
def mark_outreach_status(request):
    """AJAX view to mark email/sms as sent."""
    patient_id = request.POST.get('patient_id')
    activity_type = request.POST.get('activity_type')
    is_checked = request.POST.get('checked') == 'true'
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    if is_checked:
        PatientStatus.objects.get_or_create(
            patient=patient,
            activity_type=activity_type,
            # We use a standard description so we can find it to delete if unchecked
            description=f"Outreach marked via Report"
        )
    else:
        # Delete only records for this specific type to undo
        PatientStatus.objects.filter(
            patient=patient,
            activity_type=activity_type,
            description="Outreach marked via Report"
        ).delete()
            
    return JsonResponse({'status': 'success'})

def get_daily_outreach_data(patient_ids=None, target_date=None):
    """Get metrics and activities for a specific day or today's outreach."""
    report_date = target_date or timezone.localdate()
    start_of_day = timezone.make_aware(datetime.combine(report_date, datetime.min.time()))
    end_of_day = start_of_day + timedelta(days=1)

    if patient_ids:
        # Focus specifically on the patients just processed for the requested date
        activities = PatientStatus.objects.filter(
            activity_type__in=['Email Sent', 'SMS Sent'],
            patient_id__in=patient_ids,
            created_at__gte=start_of_day,
            created_at__lt=end_of_day,
        ).order_by('-created_at').select_related('patient')
        
        failures = ScheduledWish.objects.filter(
            status='Failed',
            patient_id__in=patient_ids,
            updated_at__gte=start_of_day,
            updated_at__lt=end_of_day,
        ).order_by('-updated_at').select_related('patient')
    else:
        # Fallback to all activity for the requested date
        activities = PatientStatus.objects.filter(
            activity_type__in=['Email Sent', 'SMS Sent'],
            created_at__gte=start_of_day,
            created_at__lt=end_of_day,
        ).order_by('-created_at').select_related('patient')
        
        failures = ScheduledWish.objects.filter(
            status='Failed',
            updated_at__gte=start_of_day,
            updated_at__lt=end_of_day,
        ).order_by('-updated_at').select_related('patient')
    
    emails_count = activities.filter(activity_type='Email Sent').count()
    sms_count = activities.filter(activity_type='SMS Sent').count()
    
    return {
        'date': report_date,
        'activities': list(activities), # Convert to list for template stability
        'failures': list(failures),     # Convert to list for template stability
        'total_sent': activities.count(),
        'total_failed': failures.count(),
        'emails_count': emails_count,
        'sms_count': sms_count,
        'site_url': settings.SITE_URL,
    }


def get_daily_birthday_data(target_date=None):
    """Get birthday totals and patient-level wish status for a specific day."""
    report_date = target_date or timezone.localdate()
    start_of_day = timezone.make_aware(datetime.combine(report_date, datetime.min.time()))
    end_of_day = start_of_day + timedelta(days=1)

    sent_activity_today_qs = PatientStatus.objects.filter(
        patient_id=OuterRef('pk'),
        activity_type__in=['Email Sent', 'SMS Sent'],
        created_at__gte=start_of_day,
        created_at__lt=end_of_day,
    )
    sent_wish_today_qs = ScheduledWish.objects.filter(
        patient_id=OuterRef('pk'),
        status='Sent',
        sent_at__gte=start_of_day,
        sent_at__lt=end_of_day,
    )
    pending_wish_qs = ScheduledWish.objects.filter(
        patient_id=OuterRef('pk'),
        status='Pending',
    )

    patients = list(
        Patient.objects.filter(
            dob__month=report_date.month,
            dob__day=report_date.day,
        ).annotate(
            has_sent_activity_today=Exists(sent_activity_today_qs),
            has_sent_wish_today=Exists(sent_wish_today_qs),
            has_pending_wish=Exists(pending_wish_qs),
        ).select_related('practice').order_by('first_name', 'last_name')
    )

    wished_count = 0
    for patient in patients:
        patient.age_turning = report_date.year - patient.dob.year
        patient.is_wished_today = patient.has_sent_activity_today or patient.has_sent_wish_today
        if patient.is_wished_today:
            wished_count += 1

    return {
        'date': report_date,
        'total_birthdays': len(patients),
        'wished_count': wished_count,
        'unwished_count': len(patients) - wished_count,
        'patients': patients,
    }


def _get_report_api_token():
    return os.getenv('REPORT_API_TOKEN') or os.getenv('DAILY_REPORT_API_TOKEN')


def _is_report_api_authorized(request):
    expected_token = _get_report_api_token()
    if not expected_token:
        return False, JsonResponse(
            {'status': 'error', 'message': 'Daily report API token is not configured.'},
            status=503
        )

    auth_header = request.headers.get('Authorization', '')
    api_key = request.headers.get('X-API-Key', '')
    provided_token = ''

    if auth_header.startswith('Bearer '):
        provided_token = auth_header[7:].strip()
    elif api_key:
        provided_token = api_key.strip()

    if provided_token != expected_token:
        return False, JsonResponse(
            {'status': 'error', 'message': 'Unauthorized daily report request.'},
            status=401
        )

    return True, None


def _serialize_daily_outreach_data(context):
    birthday_context = get_daily_birthday_data(context['date'])

    return {
        'status': 'success',
        'report': {
            'date': context['date'].isoformat(),
            'site_url': context['site_url'],
            'summary': {
                'total_sent': context['total_sent'],
                'total_failed': context['total_failed'],
                'emails_count': context['emails_count'],
                'sms_count': context['sms_count'],
                'birthdays_total': birthday_context['total_birthdays'],
                'birthdays_wished': birthday_context['wished_count'],
                'birthdays_unwished': birthday_context['unwished_count'],
            },
            'birthdays': {
                'total': birthday_context['total_birthdays'],
                'wished': birthday_context['wished_count'],
                'unwished': birthday_context['unwished_count'],
                'details': [
                    {
                        'id': patient.id,
                        'first_name': patient.first_name,
                        'last_name': patient.last_name,
                        'email': patient.email,
                        'phone': patient.phone,
                        'practice': patient.practice.name if patient.practice else None,
                        'patient_type': patient.patient_type,
                        'membership_plan': patient.membership_plan,
                        'age_turning': patient.age_turning,
                        'is_wished_today': patient.is_wished_today,
                        'has_sent_activity_today': patient.has_sent_activity_today,
                        'has_sent_wish_today': patient.has_sent_wish_today,
                        'has_pending_wish': patient.has_pending_wish,
                    }
                    for patient in birthday_context['patients']
                ],
            },
            'activities': [
                {
                    'id': activity.id,
                    'activity_type': activity.activity_type,
                    'description': activity.description,
                    'full_content': activity.full_content,
                    'created_at': timezone.localtime(activity.created_at).isoformat(),
                    'patient': {
                        'id': activity.patient_id,
                        'first_name': activity.patient.first_name,
                        'last_name': activity.patient.last_name,
                        'email': activity.patient.email,
                        'phone': activity.patient.phone,
                        'practice': activity.patient.practice.name if activity.patient.practice else None,
                    },
                }
                for activity in context['activities']
            ],
            'failures': [
                {
                    'id': failure.id,
                    'channel': failure.channel,
                    'status': failure.status,
                    'scheduled_for': timezone.localtime(failure.scheduled_for).isoformat(),
                    'updated_at': timezone.localtime(failure.updated_at).isoformat(),
                    'error_message': failure.error_message,
                    'patient': {
                        'id': failure.patient_id,
                        'first_name': failure.patient.first_name,
                        'last_name': failure.patient.last_name,
                        'email': failure.patient.email,
                        'phone': failure.patient.phone,
                        'practice': failure.patient.practice.name if failure.patient.practice else None,
                    },
                }
                for failure in context['failures']
            ],
        },
    }


@require_GET
def daily_report_api(request):
    """Token-protected JSON API for another app to fetch the daily report."""
    is_authorized, error_response = _is_report_api_authorized(request)
    if not is_authorized:
        return error_response

    report_date = timezone.localdate()
    date_param = request.GET.get('date')
    if date_param:
        try:
            report_date = date.fromisoformat(date_param)
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid date. Use YYYY-MM-DD.'},
                status=400
            )

    patient_ids = None
    patient_ids_param = request.GET.get('patient_ids', '').strip()
    if patient_ids_param:
        try:
            patient_ids = [
                int(patient_id.strip())
                for patient_id in patient_ids_param.split(',')
                if patient_id.strip()
            ]
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid patient_ids. Use comma-separated integers.'},
                status=400
            )

    context = get_daily_outreach_data(patient_ids=patient_ids, target_date=report_date)
    return JsonResponse(_serialize_daily_outreach_data(context))

def send_daily_summary_report(recipient_list=None, patient_ids=None, cc_list=None, bcc_list=None):
    """Send the daily CEO summary report."""
    print(f"Preparing summary report (Patient IDs: {patient_ids})...")
    if not recipient_list:
        recipient_list = ["bijoy@sivasolutions.com"]
        
    context = get_daily_outreach_data(patient_ids=patient_ids)
    print(f"Report metrics: Sent={context['total_sent']}, Failed={context['total_failed']}")
    
    if context['total_sent'] == 0 and context['total_failed'] == 0:
        print("No activity to report today. Skipping email.")
        return False
        
    try:
        template = 'birthday/emails/daily_summary_email.html'
        html_content = render_to_string(template, context)
        
        subject = f"Daily Outreach Summary - {context['date'].strftime('%b %d, %Y')}"

        # Use report-specific settings, falling back to defaults
        report_from_name = os.getenv('REPORT_EMAIL_FROM_NAME', settings.EMAIL_FROM_NAME)
        report_from_email = os.getenv('REPORT_DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)
        connection = get_report_email_connection()

        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=formataddr((report_from_name, report_from_email)),
            to=recipient_list,
            cc=cc_list,
            bcc=bcc_list,
            connection=connection
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        print(f"Report emailed successfully to {recipient_list}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send daily summary report: {str(e)}")
        return False

def email_daily_summary_trigger(request):
    """View trigger to manually test the daily summary report."""
    
    # Helper to parse multiple emails from comma-separated string
    def parse_emails(email_str):
        if not email_str:
            return []
        return [e.strip() for e in email_str.split(',') if e.strip()]

    recipients = parse_emails(request.GET.get('email', "bijoy@sivasolutions.com"))
    cc_list = parse_emails(request.GET.get('cc', ''))
    bcc_list = parse_emails(request.GET.get('bcc', ''))

    if not recipients:
        recipients = ["bijoy@sivasolutions.com"]

    success = send_daily_summary_report(recipients, cc_list=cc_list, bcc_list=bcc_list)
    
    if success:
        return JsonResponse({'status': 'success', 'message': f'Daily summary sent to {", ".join(recipients)}'})
    else:
        # Check if they want to send it even if empty
        force = request.GET.get('force') == 'true'
        if force:
            context = get_daily_outreach_data()
            template = 'birthday/emails/daily_summary_email.html'
            html_content = render_to_string(template, context)
            subject = f"Daily Outreach Summary (Manual) - {context['date'].strftime('%b %d, %Y')}"

            # Use report-specific settings, falling back to defaults
            report_from_name = os.getenv('REPORT_EMAIL_FROM_NAME', settings.EMAIL_FROM_NAME)
            report_from_email = os.getenv('REPORT_DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)
            connection = get_report_email_connection()

            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=formataddr((report_from_name, report_from_email)),
                to=recipients,
                cc=cc_list,
                bcc=bcc_list,
                connection=connection
            )
            email.content_subtype = "html"
            email.send()
            return JsonResponse({'status': 'success', 'message': f'Forced daily summary sent to {", ".join(recipients)}'})
        
        return JsonResponse({'status': 'error', 'message': 'No activity today to report. Use force=true to send anyway.'})
