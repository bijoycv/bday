from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime, date
from django.http import HttpResponse, JsonResponse
from .models import PatientStatus, ScheduledWish, Patient
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from xhtml2pdf import pisa
import io

def report_dashboard(request):
    """View to show the report selection page."""
    return render(request, 'birthday/reports/dashboard.html')

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

from django.core.mail import EmailMessage
from django.conf import settings
from email.utils import formataddr

def send_report_email(period='weekly', report_type='birthday', recipient_list=None):
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
    
    email = EmailMessage(
        subject,
        html_content,
        formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
        recipient_list
    )
    email.content_subtype = "html"
    email.send()
    return True

def email_report_trigger(request):
    """View trigger to manually test the email report."""
    period = request.GET.get('period', 'weekly')
    report_type = request.GET.get('type', 'birthday')
    recipient = request.GET.get('email', "bijoy@sivasolutions.com")
    
    success = send_report_email(period, report_type, [recipient])
    
    if success:
        return JsonResponse({'status': 'success', 'message': f'Report email sent to {recipient}'})
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

def get_daily_outreach_data(patient_ids=None):
    """Get metrics and activities for today's outreach or specific IDs."""
    today = timezone.localdate()
    
    start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    
    if patient_ids:
        # Focus specifically on the patients just processed, but only for today
        activities = PatientStatus.objects.filter(
            activity_type__in=['Email Sent', 'SMS Sent'],
            patient_id__in=patient_ids,
            created_at__gte=start_of_day
        ).order_by('-created_at').select_related('patient')
        
        failures = ScheduledWish.objects.filter(
            status='Failed',
            patient_id__in=patient_ids,
            updated_at__gte=start_of_day
        ).order_by('-updated_at').select_related('patient')
    else:
        # Fallback to today's activity
        activities = PatientStatus.objects.filter(
            activity_type__in=['Email Sent', 'SMS Sent'],
            created_at__gte=start_of_day
        ).order_by('-created_at').select_related('patient')
        
        failures = ScheduledWish.objects.filter(
            status='Failed',
            updated_at__gte=start_of_day
        ).order_by('-updated_at').select_related('patient')
    
    emails_count = activities.filter(activity_type='Email Sent').count()
    sms_count = activities.filter(activity_type='SMS Sent').count()
    
    return {
        'date': today,
        'activities': list(activities), # Convert to list for template stability
        'failures': list(failures),     # Convert to list for template stability
        'total_sent': activities.count(),
        'total_failed': failures.count(),
        'emails_count': emails_count,
        'sms_count': sms_count,
        'site_url': settings.SITE_URL,
    }

def send_daily_summary_report(recipient_list=None, patient_ids=None):
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
        
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
            to=recipient_list
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
    recipient = request.GET.get('email', "bijoy@sivasolutions.com")
    success = send_daily_summary_report([recipient])
    
    if success:
        return JsonResponse({'status': 'success', 'message': f'Daily summary sent to {recipient}'})
    else:
        # Check if they want to send it even if empty
        force = request.GET.get('force') == 'true'
        if force:
            context = get_daily_outreach_data()
            template = 'birthday/emails/daily_summary_email.html'
            html_content = render_to_string(template, context)
            subject = f"Daily Outreach Summary (Manual) - {context['date'].strftime('%b %d, %Y')}"
            email = EmailMessage(
                subject,
                html_content,
                formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
                [recipient]
            )
            email.content_subtype = "html"
            email.send()
            return JsonResponse({'status': 'success', 'message': f'Forced daily summary sent to {recipient}'})
        
        return JsonResponse({'status': 'error', 'message': 'No activity today to report. Use force=true to send anyway.'})
