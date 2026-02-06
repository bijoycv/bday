import pytz
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Patient, MessageTemplate, ScheduledWish, SavedRecipient, PatientStatus, EmailSignature, clean_phone_number, PlanHistory, Practice
from .forms import PatientForm, UploadFileForm, MessageTemplateForm, ScheduledWishForm, SavedRecipientForm, EmailSignatureForm
from datetime import datetime, date, timedelta
from django.db.models.functions import ExtractMonth, ExtractDay
import re
import os
import requests
from django.conf import settings
from django.db.models import Q, Sum

def index(request):
    """
    Renders the dashboard index page with comprehensive statistics.
    """
    today = date.today()
    total_patients = Patient.objects.count()
    
    # Membership statistics
    active_count = Patient.objects.filter(
        enrollment_date__gte=today - timedelta(days=365)
    ).count()
    
    expiring_soon_count = Patient.objects.filter(
        enrollment_date__lt=today - timedelta(days=335),
        enrollment_date__gte=today - timedelta(days=365)
    ).count()
    
    just_expired_count = Patient.objects.filter(
        enrollment_date__lt=today - timedelta(days=365),
        enrollment_date__gte=today - timedelta(days=395)
    ).count()
    
    expired_total_count = Patient.objects.filter(
        enrollment_date__lt=today - timedelta(days=365)
    ).count()

    proceed_count = Patient.objects.filter(patient_type='Proceed').count()
    regular_count = Patient.objects.filter(patient_type='Regular').count()

    # Card Types statistics (Active Plans only)
    gold_count = Patient.objects.filter(
        membership_plan='Gold',
        enrollment_date__gte=today - timedelta(days=365)
    ).count()
    
    silver_count = Patient.objects.filter(
        membership_plan='Silver',
        enrollment_date__gte=today - timedelta(days=365)
    ).count()
    
    bronze_count = Patient.objects.filter(
        membership_plan='Bronze',
        enrollment_date__gte=today - timedelta(days=365)
    ).count()

    # Get upcoming birthdays (Top 5)
    all_patients = Patient.objects.all()
    
    # Sort by upcoming birthdays logic
    def days_until_next_birthday(patient):
        if not patient.dob:
            return 9999
        bday = patient.dob
        try:
            this_year_bday = date(today.year, bday.month, bday.day)
        except ValueError: # Leap year case
            this_year_bday = date(today.year, 3, 1)
            
        if this_year_bday < today:
            try:
                next_year_bday = date(today.year + 1, bday.month, bday.day)
            except ValueError:
                next_year_bday = date(today.year + 1, 3, 1)
            return (next_year_bday - today).days
        return (this_year_bday - today).days

    # Convert to list and sort
    patient_list_sorted = sorted(list(all_patients), key=days_until_next_birthday)
    upcoming_patients = patient_list_sorted[:5] # Show only 5 for a compact dashboard
    
    # For each patient, check if they have a pending scheduled wish
    for p in upcoming_patients:
        p.has_scheduled = ScheduledWish.objects.filter(patient=p, status='Pending').exists()
        # Calculate age turning
        if p.dob:
            bday = p.dob
            this_year_bday = date(today.year, bday.month, bday.day)
            if this_year_bday < today:
                p.age_turning = today.year + 1 - bday.year
            else:
                p.age_turning = today.year - bday.year

    # Analytics: Plan Upgrades & Downgrades (Last 6 Months)
    import json
    chart_months = []
    upgrades_data = []
    downgrades_data = []
    renewals_data = []
    
    for i in range(5, -1, -1):
        first_of_month = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_label = first_of_month.strftime('%b')
        chart_months.append(month_label)
        
        if first_of_month.month == 12:
            next_month = first_of_month.replace(year=first_of_month.year + 1, month=1)
        else:
            next_month = first_of_month.replace(month=first_of_month.month + 1)
            
        up_count = PlanHistory.objects.filter(
            change_type='Upgrade',
            created_at__gte=first_of_month,
            created_at__lt=next_month
        ).count()
        
        down_count = PlanHistory.objects.filter(
            change_type='Downgrade',
            created_at__gte=first_of_month,
            created_at__lt=next_month
        ).count()

        ren_count = PlanHistory.objects.filter(
            change_type='Renewal',
            created_at__gte=first_of_month,
            created_at__lt=next_month
        ).count()
        
        upgrades_data.append(up_count)
        downgrades_data.append(down_count)
        renewals_data.append(ren_count)

    # Total Transition Stats for Pie Chart
    total_up = PlanHistory.objects.filter(change_type='Upgrade').count()
    total_down = PlanHistory.objects.filter(change_type='Downgrade').count()
    total_ren = PlanHistory.objects.filter(change_type='Renewal').count()

    context = {
        'total_patients': total_patients,
        'proceed_count': proceed_count,
        'regular_count': regular_count,
        'active_count': active_count,
        'expiring_soon_count': expiring_soon_count,
        'just_expired_count': just_expired_count,
        'expired_total_count': expired_total_count,
        'gold_count': gold_count,
        'silver_count': silver_count,
        'bronze_count': bronze_count,
        'upcoming_birthdays': upcoming_patients,
        'chart_labels': json.dumps(chart_months),
        'chart_upgrades': json.dumps(upgrades_data),
        'chart_downgrades': json.dumps(downgrades_data),
        'chart_renewals': json.dumps(renewals_data),
        'total_up': total_up,
        'total_down': total_down,
        'total_ren': total_ren,
    }
    return render(request, 'index.html', context)

from django.core.paginator import Paginator
from django.db.models import Q

# ... (existing imports)

def patient_list(request):
    patients = Patient.objects.all()
    
    # 1. Search Logic
    search_query = request.GET.get('q', '')
    if search_query:
        from django.db.models import Value
        from django.db.models.functions import Concat

        patients = patients.annotate(
            full_name=Concat('first_name', Value(' '), 'last_name')
        ).filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # 2. Month Filter Logic
    month_filter = request.GET.get('month', '')
    if month_filter:
        try:
            month_int = int(month_filter)
            patients = patients.filter(dob__month=month_int)
        except ValueError:
            pass

    # 3. Status Filter Logic (Proceed Status)
    status_filter = request.GET.get('status', '')
    today = date.today()

    if status_filter == 'proceed_active':
        patients = patients.filter(
            patient_type='Proceed',
            enrollment_date__gte=today - timedelta(days=365)
        )
    elif status_filter == 'proceed_inactive':
        patients = patients.filter(patient_type='Proceed').filter(
            Q(enrollment_date__lt=today - timedelta(days=365)) |
            Q(enrollment_date__isnull=True)
        )
    elif status_filter == 'expiring_soon':
        patients = patients.filter(
            patient_type='Proceed',
            enrollment_date__lt=today - timedelta(days=335),
            enrollment_date__gte=today - timedelta(days=365)
        )
    elif status_filter == 'not_registered':
        patients = patients.filter(patient_type='Regular')

    # 3.5. Patient Type Filter Logic
    patient_type_filter = request.GET.get('patient_type', '')
    if patient_type_filter:
        patients = patients.filter(patient_type=patient_type_filter)

    # 3.6. Plan Filter Logic
    plan_filter = request.GET.get('plan', '')
    if plan_filter:
        patients = patients.filter(membership_plan=plan_filter)

    # 4. Sorting & Pagination Prep
    sort_mode = request.GET.get('sort', '')
    default_sort = 'recent'
    
    if month_filter:
        # When filtering by month, 'upcoming' makes less sense than just sorting 1-31.
        if not sort_mode or sort_mode == 'upcoming':
            sort_mode = 'day'
    else:
        if not sort_mode:
            sort_mode = 'recent'

    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    if sort_mode == 'upcoming':
        today = date.today()
        # Convert to list for complex sorting
        items_list = list(patients)
        
        def days_until_next_birthday(patient):
            if not patient.dob:
                return 9999
            bday = patient.dob
            try:
                this_year_bday = bday.replace(year=today.year)
            except ValueError:
                this_year_bday = bday.replace(month=3, day=1, year=today.year)

            if this_year_bday < today:
                try:
                    next_bday = bday.replace(year=today.year + 1)
                except ValueError:
                     next_bday = bday.replace(month=3, day=1, year=today.year + 1)
                return (next_bday - today).days
            else:
                return (this_year_bday - today).days

        items_list.sort(key=days_until_next_birthday)
        patients = items_list
    elif sort_mode == 'recent':
        # Combined sort for Recently Added and Recently Updated (plan/details)
        patients = patients.order_by('-updated_at')
    elif sort_mode == 'day':
        # Sort by day of month (useful when filtering by specific month)
        patients = patients.annotate(day=ExtractDay('dob')).order_by('day')
    else:
        # Default sort
        patients = patients.order_by('-updated_at')

    # Prefetch activities for the Timeline column
    if isinstance(patients, list):
        # Already a list (from upcoming sort), prefetching is different or handled manually if needed
        pass
    else:
        patients = patients.prefetch_related('activities')

    paginator = Paginator(patients, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get objects for the send message modal
    templates = MessageTemplate.objects.all().select_related('signature')
    signatures = EmailSignature.objects.all()
    saved_cc = SavedRecipient.objects.filter(recipient_type='CC')
    saved_bcc = SavedRecipient.objects.filter(recipient_type='BCC')

    # Data for filters
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    available_plans = [p[0] for p in Patient.MEMBERSHIP_PLAN_CHOICES]
    last_active = Patient.objects.order_by('-updated_at').first()
    practices = Practice.objects.all()
            
    context = {
        'patients': page_obj,
        'page_obj': page_obj,
        'templates': templates,
        'signatures': signatures,
        'saved_cc': saved_cc,
        'saved_bcc': saved_bcc,
        'months': months,
        'available_plans': available_plans,
        'last_active': last_active,
        'practices': practices,
        'search_query': search_query,
        'month_filter': month_filter,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
        'patient_type_filter': patient_type_filter,
        'current_sort': sort_mode,
        'per_page': per_page,
        'today': date.today(),
    }
    return render(request, 'birthday/patient_list.html', context)

def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'birthday/patient_detail.html', {'patient': patient})

def parse_patient_file(file):
    """
    Parses the uploaded text file and returns a dictionary of patient data.
    """
    data = {}
    content = file.read().decode('utf-8')
    lines = content.splitlines()

    # Mapping from file keys to model fields
    field_map = {
        'patient': 'first_name',
        'middle_name': 'middle_name',
        'last_name': 'last_name',
        'dob': 'dob',
        'PatientPhone': 'phone',
        'PatientEmail': 'email',
        'PUT_Address': 'address',
        'PUT_City': 'city',
        'PUT_State': 'state',
        'PUT_ZipCode': 'zip_code',
        'PUT_TodaysDate': 'enrollment_date',
        # 'Result': 'payment_amount', # Removed as we use payment_method now
    }
    
    membership_plan = None
    payment_method = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to match key-value pair pattern: TYPE^KEY VALUE or just remaining text
        parts = line.split(' ', 1)
        if len(parts) < 2:
            continue
            
        key_part = parts[0]
        value = parts[1].strip()
        
        if '^' in key_part:
            _, key = key_part.split('^', 1)
        else:
            continue # Skip lines that don't match format

        # Handle specific fields
        if key in field_map:
            model_field = field_map[key]
            
            # Date conversion
            if model_field in ['dob', 'enrollment_date']:
                try:
                    date_obj = datetime.strptime(value, '%m/%d/%Y')
                    value = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pass # Keep original string or handle error
            
            data[model_field] = value
        
        # Handle Radio Buttons
        if key_part.startswith('RB^') and value == 'True':
            # Membership Plan: e.g. PUT_BronzePlan_SFYS -> Bronze
            if 'Plan_SFYS' in key:
                plan_name = key.replace('PUT_', '').replace('Plan_SFYS', '').replace('_', ' ')
                # Ensure it matches choices if possible, capitalize
                membership_plan = plan_name.capitalize()
            
            # Payment Method: e.g. PUT_CreditCard_SFYS -> Credit Card
            if 'CreditCard' in key:
                payment_method = 'Credit Card'
            elif 'Cash' in key: # Assuming PUT_Cash_SFYS
                payment_method = 'Cash'

    if membership_plan:
        data['membership_plan'] = membership_plan
        data['patient_type'] = 'Proceed'
    else:
        # Default Regular if no plan found
        data['patient_type'] = 'Regular'
        # Ensure membership_plan is not set to avoid validation errors if model enforced choices strictly (it allows blank though)

    if payment_method:
        data['payment_method'] = payment_method
        
    return data

def parse_pasted_patient_data(text):
    """
    Parses pasted text content in specific User-provided format (Key:Value)
    Supports both line-separated and comma-separated formats.
    """
    data = {}
    
    # Normalize separators: if many commas and few newlines, likely comma-separated export
    if ',' in text and (text.count(',') > text.count('\n')):
        # Split by comma, but be wary of commas in values (less likely in this specific export)
        items = text.replace('\n', ',').split(',')
    else:
        items = text.splitlines()

    membership_plan = None
    payment_method = None
    
    for item in items:
        if ':' not in item:
            continue
            
        key, value = item.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        
        if not value or value.lower() in ['none', 'null', '']:
            continue
            
        # Full Name (Old format)
        if key == 'name':
            parts = value.split()
            if len(parts) >= 2:
                data['first_name'] = parts[0]
                data['last_name'] = " ".join(parts[1:])
            else:
                data['first_name'] = value
                data['last_name'] = ""
        
        # Split Name (New format)
        elif key == 'first_name':
            data['first_name'] = value
        elif key == 'last_name':
            data['last_name'] = value
        elif key == 'middle_name':
            data['middle_name'] = value
            
        # Email
        elif key in ['email', 'email address']:
            data['email'] = value
            
        # Phone
        elif key in ['phone', 'phone number', 'mobile_number', 'mobile phone', 'mobile']:
            data['phone'] = value
            
        # DOB
        elif key in ['dob', 'date of birth', 'birth date', 'date_of_birth']:
            # Handle multiple date formats
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y']
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    data['dob'] = date_obj.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
        
        # New Fields (Gender, Notes)
        elif key == 'gender':
            # Normalize to choices: Male, Female, Other
            val_lower = value.lower()
            if val_lower.startswith('f'): data['gender'] = 'Female'
            elif val_lower.startswith('m'): data['gender'] = 'Male'
            else: data['gender'] = 'Other'
        elif key == 'notes':
            data['notes'] = value
                
        # Address Fields
        elif key == 'address':
            data['address'] = value
        elif key == 'city':
            data['city'] = value
        elif key == 'state':
            data['state'] = value
        elif key == 'zip code':
            data['zip_code'] = value
        
        # Enrollment Date
        elif key == 'todays date':
            try:
                date_obj = datetime.strptime(value, '%m/%d/%Y')
                data['enrollment_date'] = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass

        # Membership and Payment checks (value is 'Yes' - old format)
        elif str(value).lower() == 'yes':
             if 'bronze plan' in key:
                 membership_plan = 'Bronze'
             elif 'silver plan' in key:
                 membership_plan = 'Silver'
             elif 'gold plan' in key:
                 membership_plan = 'Gold'
             elif 'cash' in key:
                 payment_method = 'Cash'
             elif 'credit' in key:
                 payment_method = 'Credit Card'
                 
    if membership_plan:
        data['membership_plan'] = membership_plan
        data['patient_type'] = 'Proceed'
    else:
        # Default Regular if no plan found but allow logic to proceed
        if 'patient_type' not in data:
            data['patient_type'] = 'Regular'

    if payment_method:
        data['payment_method'] = payment_method
        
    return data

def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        upload_form = UploadFileForm(request.POST, request.FILES)
        
        if 'upload_file' in request.POST:
                files = request.FILES.getlist('file')
                if not files:
                    messages.error(request, "No files selected.")
                    return redirect('patient_list')

                success_count = 0
                error_count = 0
                duplicate_count = 0
                errors = []
                duplicates = []

                for file in files:
                    try:
                        patient_data = parse_patient_file(file)
                        
                        # Check for existing patient
                        email = patient_data.get('email')
                        phone = clean_phone_number(patient_data.get('phone', ''))
                        fname = patient_data.get('first_name')
                        lname = patient_data.get('last_name')
                        dob = patient_data.get('dob')
                        new_enrollment_date = patient_data.get('enrollment_date')
                        
                        existing_patient = None
                        if email:
                            existing_patient = Patient.objects.filter(email=email).first()
                        
                        if not existing_patient and phone:
                            existing_patient = Patient.objects.filter(phone=phone).first()

                        # Fallback: Check for Name + DOB if no email/phone match found
                        if not existing_patient and fname and lname and dob:
                            existing_patient = Patient.objects.filter(
                                first_name__iexact=fname,
                                last_name__iexact=lname,
                                dob=dob
                            ).first()

                        if existing_patient:
                            name = f"{existing_patient.first_name} {existing_patient.last_name}"
                            
                            # Determine if plan was upgraded, downgraded or renewed
                            old_plan = existing_patient.membership_plan
                            new_plan = patient_data.get('membership_plan')
                            
                            plan_ranks = {'Bronze': 1, 'Silver': 2, 'Gold': 3}
                            old_rank = plan_ranks.get(old_plan, 0)
                            new_rank = plan_ranks.get(new_plan, 0)
                            
                            if new_rank > old_rank:
                                update_desc = f"Plan upgraded from {old_plan} to {new_plan}"
                            elif new_rank < old_rank:
                                update_desc = f"Plan downgraded from {old_plan} to {new_plan}"
                            else:
                                update_desc = f"Plan renewed to {new_plan}"
                            # Convert existing date for comparison if it's a date object
                            existing_enrollment_date = str(existing_patient.enrollment_date) if existing_patient.enrollment_date else None

                            # If enrollment date is different, update the patient (Renewal/Update)
                            if new_enrollment_date and new_enrollment_date != existing_enrollment_date:
                                # Update fields
                                for key, val in patient_data.items():
                                    setattr(existing_patient, key, val)
                                existing_patient.save()
                                
                                # Log update activity
                                PatientStatus.objects.create(
                                    patient=existing_patient,
                                    activity_type='Plan Updated',
                                    description=update_desc,
                                    full_content=f"Patient automatically updated during import. New Enrollment Date: {new_enrollment_date}"
                                )
                                success_count += 1
                                continue
                            else:
                                # Truly a duplicate (same enrollment date or no new date)
                                duplicate_count += 1
                                duplicates.append(f"<strong>{name}</strong> - Email: {email or 'N/A'}")
                                continue

                        # Create a form with the parsed data to validate it
                        patient_form = PatientForm(data=patient_data)
                        if patient_form.is_valid():
                            new_patient = patient_form.save()
                            PatientStatus.objects.create(
                                patient=new_patient,
                                activity_type='Added',
                                description=f"Patient imported via file: {file.name}"
                            )
                            success_count += 1
                        else:
                            error_count += 1
                            # Collect formatted errors
                            err_msg = []
                            for field, error_list in patient_form.errors.items():
                                err_msg.append(f"{field}: {', '.join(error_list)}")
                            errors.append(f"{file.name}: {'; '.join(err_msg)}")
                    except Exception as e:
                        error_count += 1
                        errors.append(f"{file.name}: {str(e)}")
                
                # Report results
                if success_count > 0:
                    messages.success(request, f'Successfully imported {success_count} patient(s).')
                
                if duplicate_count > 0:
                     # Create a formatted list of duplicates
                     dup_list = "<ul class='mb-0 text-start'>"
                     for d in duplicates[:5]:  # Show first 5
                         dup_list += f"<li>{d}</li>"
                     if len(duplicates) > 5:
                         dup_list += f"<li>...and {len(duplicates)-5} others</li>"
                     dup_list += "</ul>"
                     
                     messages.warning(request, f'Skipped {duplicate_count} duplicate patient(s):<br>{dup_list}', extra_tags='safe')

                if error_count > 0:
                    # Show first few errors to avoid screen clutter
                    errors_display = "<br>".join(errors[:5])
                    if len(errors) > 5:
                        errors_display += f"<br>...and {len(errors)-5} more."
                    messages.error(request, f'Failed to import {error_count} file(s):<br>{errors_display}', extra_tags='safe')
                
                return redirect('patient_list')
        
        elif 'paste_content' in request.POST:
            raw_content = request.POST.get('raw_content', '')
            if not raw_content:
                messages.error(request, "No content pasted.")
                return redirect('patient_list')

            try:
                patient_data = parse_pasted_patient_data(raw_content)
                if not patient_data:
                     messages.error(request, "Could not parse any patient data from content.")
                     return redirect('patient_list')

                # Common reuse logic - adapted from file upload
                # Check for existing patient
                email = patient_data.get('email')
                phone = clean_phone_number(patient_data.get('phone', ''))
                fname = patient_data.get('first_name')
                lname = patient_data.get('last_name')
                dob = patient_data.get('dob')
                new_enrollment_date = patient_data.get('enrollment_date')
                
                existing_patient = None
                if email:
                    existing_patient = Patient.objects.filter(email=email).first()
                
                if not existing_patient and phone:
                    existing_patient = Patient.objects.filter(phone=phone).first()

                if not existing_patient and fname and lname and dob:
                    existing_patient = Patient.objects.filter(
                        first_name__iexact=fname,
                        last_name__iexact=lname,
                        dob=dob
                    ).first()

                if existing_patient:
                    # Update Logic
                    old_plan = existing_patient.membership_plan
                    new_plan = patient_data.get('membership_plan')
                    
                    plan_ranks = {'Bronze': 1, 'Silver': 2, 'Gold': 3}
                    old_rank = plan_ranks.get(old_plan, 0)
                    new_rank = plan_ranks.get(new_plan, 0)
                    
                    if new_rank > old_rank:
                        update_desc = f"Plan upgraded from {old_plan} to {new_plan}"
                    elif new_rank < old_rank:
                        update_desc = f"Plan downgraded from {old_plan} to {new_plan}"
                    else:
                        update_desc = f"Plan renewed to {new_plan}"

                    existing_enrollment_date = str(existing_patient.enrollment_date) if existing_patient.enrollment_date else None

                    if new_enrollment_date and new_enrollment_date != existing_enrollment_date:
                        for key, val in patient_data.items():
                            setattr(existing_patient, key, val)
                        existing_patient.save()
                        
                        PatientStatus.objects.create(
                            patient=existing_patient,
                            activity_type='Plan Updated',
                            description=update_desc,
                            full_content=f"Patient automatically updated via pasted content. New Enrollment Date: {new_enrollment_date}"
                        )
                        messages.success(request, f"Patient {existing_patient} updated successfully (Renewal/Upgrade).")
                    else:
                        messages.warning(request, f"Patient {existing_patient} already exists and is up to date.")
                else:
                    # Create New Logic
                    patient_form = PatientForm(data=patient_data)
                    if patient_form.is_valid():
                        new_patient = patient_form.save()
                        PatientStatus.objects.create(
                            patient=new_patient,
                            activity_type='Added',
                            description="Patient imported via text paste"
                        )
                        messages.success(request, f"Patient {new_patient} created successfully!")
                    else:
                        # Error handling
                        err_msg = []
                        for field, error_list in patient_form.errors.items():
                            err_msg.append(f"{field}: {', '.join(error_list)}")
                        messages.error(request, f"Validation Error: {'; '.join(err_msg)}")

            except Exception as e:
                messages.error(request, f"Error processing content: {str(e)}")

            return redirect('patient_list')
        
        elif 'save_patient' in request.POST:
            if form.is_valid():
                new_patient = form.save()
                PatientStatus.objects.create(
                    patient=new_patient,
                    activity_type='Added',
                    description="Patient created manually"
                )
                messages.success(request, 'Patient created successfully!')
                return redirect('patient_list')

    else:
        form = PatientForm()
        upload_form = UploadFileForm()

    return render(request, 'birthday/patient_form.html', {
        'form': form,
        'upload_form': upload_form
    })

def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            # Check for plan changes
            old_plan = patient.membership_plan
            updated_patient = form.save()
            new_plan = updated_patient.membership_plan
            
            activity_type = 'Details Updated'
            description = "Patient details were updated"
            
            if old_plan != new_plan:
                activity_type = 'Plan Updated'
                description = f"Plan changed from {old_plan} to {new_plan}"
                
            PatientStatus.objects.create(
                patient=updated_patient,
                activity_type=activity_type,
                description=description
            )
            
            messages.success(request, 'Patient updated successfully!')
            return redirect('patient_list')
    else:
        form = PatientForm(instance=patient)
    
    # Empty upload form just for template compatibility if needed, though update usually no upload
    return render(request, 'birthday/patient_form.html', {
        'form': form,
        'patient': patient,
        'is_edit': True
    })

def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, 'Patient deleted successfully!')
        return redirect('patient_list')
    return render(request, 'birthday/patient_confirm_delete.html', {'patient': patient})

def patient_bulk_delete(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_patients')
        if selected_ids:
            # Filter and delete
            patients = Patient.objects.filter(pk__in=selected_ids)
            count = patients.count()
            patients.delete()
            messages.success(request, f'Successfully deleted {count} patient(s).')
        else:
            messages.warning(request, 'No patients selected for deletion.')
            
    return redirect('patient_list')

from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def toggle_patient_verification(request, pk):
    """
    Toggle the verified status of a patient.
    """
    patient = get_object_or_404(Patient, pk=pk)
    patient.is_verified = not patient.is_verified
    patient.save()
    
    return JsonResponse({
        'status': 'success', 
        'is_verified': patient.is_verified,
        'message': 'Patient verification status updated.'
    })

# --- Template Management Views ---
from .models import MessageTemplate, ScheduledWish
from .forms import MessageTemplateForm, ScheduledWishForm

def template_list(request):
    templates = MessageTemplate.objects.all()
    return render(request, 'birthday/template_list.html', {'templates': templates})

def template_create(request):
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template created successfully!')
            return redirect('template_list')
    else:
        form = MessageTemplateForm()
    return render(request, 'birthday/template_form.html', {'form': form, 'title': 'Create Template'})

def template_update(request, pk):
    template = get_object_or_404(MessageTemplate, pk=pk)
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template updated successfully!')
            return redirect('template_list')
    else:
        form = MessageTemplateForm(instance=template)
    return render(request, 'birthday/template_form.html', {'form': form, 'title': 'Edit Template'})

def template_delete(request, pk):
    template = get_object_or_404(MessageTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Template deleted successfully!')
        return redirect('template_list')
    return redirect('template_list')

# --- Scheduled Wishes Views ---
from django.core.paginator import Paginator

def scheduled_list(request):
    # Filter by status if provided
    status_filter = request.GET.get('status')
    per_page = request.GET.get('per_page', 10)
    
    # Get all wishes ordered by scheduled_for in reverse (newest first)
    wishes_list = ScheduledWish.objects.all().order_by('-scheduled_for')
    
    if status_filter:
        wishes_list = wishes_list.filter(status=status_filter)
        
    paginator = Paginator(wishes_list, per_page)
    page_number = request.GET.get('page')
    wishes = paginator.get_page(page_number)
        
    return render(request, 'birthday/scheduled_list.html', {
        'wishes': wishes, 
        'current_status': status_filter,
        'per_page': int(per_page),
        'templates': MessageTemplate.objects.all(),
        'saved_cc': SavedRecipient.objects.filter(recipient_type='CC'),
        'saved_bcc': SavedRecipient.objects.filter(recipient_type='BCC'),
        'signatures': EmailSignature.objects.all(),
    })
    
def schedule_wish(request, patient_id=None):
    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)
        initial_data = {'patient': patient}
    else:
        initial_data = {}

    if request.method == 'POST':
        form = ScheduledWishForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Birthday wish scheduled successfully!')
            return redirect('scheduled_list')
    else:
        form = ScheduledWishForm(initial=initial_data)

    return render(request, 'birthday/schedule_form.html', {'form': form})

def quick_send_message(request):
    """Handle quick message sending from the patient list modal."""
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        message_type = request.POST.get('message_type', 'Email')
        subject = request.POST.get('subject', '')
        body = request.POST.get('body', '')
        # CC/BCC handled below
        
        patient = get_object_or_404(Patient, pk=patient_id)
        
        # Replace placeholders in subject and body
        subject = subject.replace('{first_name}', patient.first_name)
        subject = subject.replace('{last_name}', patient.last_name)
        
        body = body.replace('{first_name}', patient.first_name)
        body = body.replace('{last_name}', patient.last_name)
        
        signature_id = request.POST.get('signature_id')
        custom_signature_content = request.POST.get('custom_signature_content', '')
        signature_content = ""
        
        if custom_signature_content and message_type == 'Email':
            signature_content = custom_signature_content
        elif signature_id and message_type == 'Email':
            try:
                sig = EmailSignature.objects.get(pk=signature_id)
                signature_content = sig.content
            except EmailSignature.DoesNotExist:
                pass
        
        # Determine if we are Scheduling or Sending Now
        is_scheduled = 'schedule_now' in request.POST
        
        if is_scheduled:
            # Handle Scheduling
            
            # Use 'America/Los_Angeles' as requested
            tz = pytz.timezone('America/Los_Angeles')
            today = datetime.now(tz).date()
            
            # Default to next birthday 6am if no date provided? 
            # Or use specific date input from form if we add it?
            # For this request "morning 6.00 clock california time", 
            # let's assume if it's a birthday wish, it's next birthday.
            next_bday = patient.dob
            try:
                this_year_bday = next_bday.replace(year=today.year)
            except ValueError:
                this_year_bday = next_bday.replace(month=3, day=1, year=today.year)
            
            if this_year_bday < today:
                try:
                    target_date = next_bday.replace(year=today.year + 1)
                except ValueError:
                    target_date = next_bday.replace(month=3, day=1, year=today.year + 1)
            else:
                target_date = this_year_bday
                
            # Create scheduled Datetime: Target Date at Selected Time (PST)
            # Combine Date + Time
            schedule_time_str = request.POST.get('schedule_time', '06:00')
            try:
                # Parse HH:MM
                h, m = map(int, schedule_time_str.split(':'))
                target_time = datetime.min.time().replace(hour=h, minute=m)
            except (ValueError, AttributeError):
                target_time = datetime.min.time().replace(hour=6, minute=0)

            naive_dt = datetime.combine(target_date, target_time)
            scheduled_dt = tz.localize(naive_dt)

            cc_list = request.POST.getlist('cc_recipients')
            bcc_list = request.POST.getlist('bcc_recipients')
            
            # If we have a template in context (which we don't directly here easily without lookup, 
            # we'll create a ScheduledWish without a template_id foreign key but potentially store content?
            # The ScheduledWish model expects a 'template' FK. 
            # If this is a custom message, we might need a "Custom" template or allow null.
            # Model definition: template = models.ForeignKey(..., null=True, blank=True) -> Good.
            
            # We need to store the Body somewhere. The current ScheduledWish model 
            # might not have a free-text body field if it relies solely on Template FK.
            # Checking model: ScheduledWish has NO 'body' field, only 'template'.
            # To support custom body scheduling, we need to add a body field to ScheduledWish or 
            # create a temporary template.
            # For now, let's try to find if a template was selected.
            template_id = request.POST.get('template_id')
            template_obj = None
            if template_id:
                template_obj = MessageTemplate.objects.filter(pk=template_id).first()
            
            # If no template object, we can't save the custom body in the current schema 
            # without modifying ScheduledWish.
            # Let's assume for this specific request we might need to modify the model 
            # OR we just rely on the selected template. 
            # If the user edited the body in the editor, that edit is lost if we only save the Template ID.
            
            # *** CRITICAL: To support edited messages, we should add 'custom_body' and 'custom_subject' to ScheduledWish.
            # Check models.py again in next step if needed. 
            # For now, saving what we can.
            
            ScheduledWish.objects.create(
                patient=patient,
                template=template_obj,
                custom_subject=subject,
                custom_body=body,
                scheduled_for=scheduled_dt,
                status='Pending',
                cc_recipients=",".join(cc_list),
                bcc_recipients=",".join(bcc_list)
            )
            
            messages.success(request, f'Message scheduled for {target_date.strftime("%b %d, %Y")} at {schedule_time_str} (CA Time).')
            return redirect('patient_list')

        # Send Now Logic
        if message_type == 'Email':
            from django.core.mail import EmailMessage
            try:
                # Get CC/BCC lists from checkboxes
                cc_list = request.POST.getlist('cc_recipients')
                bcc_list = request.POST.getlist('bcc_recipients')
                
                # Check if body is already HTML (from Quill editor)
                # If it contains HTML tags, don't add extra <br> for newlines
                if '<p>' in body or '<br>' in body or '<div>' in body:
                    html_body = body
                    # Fix Quill's paragraph spacing - add inline style to remove margins
                    html_body = html_body.replace('<p>', '<p style="margin:0;padding:0;">')
                else:
                    # Plain text - convert newlines to HTML
                    html_body = body.replace('\n', '<br>')
                
                # Append signature with minimal spacing
                if signature_content:
                    # Also fix paragraph spacing in signature
                    fixed_signature = signature_content.replace('<p>', '<p style="margin:0;padding:0;">')
                    html_body += "<br>" + fixed_signature
                
                email = EmailMessage(
                    subject=subject,
                    body=html_body,
                    from_email=None,
                    to=[patient.email],
                    cc=cc_list,
                    bcc=bcc_list,
                )
                email.content_subtype = "html"  # Main content is now text/html
                email.send(fail_silently=False)
                
                # Full content for logging
                log_content = body
                if signature_content:
                    log_content += "\n\n---\nSignature: " + signature_content
                
                # Record activity
                PatientStatus.objects.create(
                    patient=patient,
                    activity_type='Email Sent',
                    description=f"Subject: {subject}",
                    full_content=log_content
                )
                
                messages.success(request, f'Email sent successfully to {patient.first_name}!')
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Failed to send email: {str(e)}')
        else:
            # Twilio SMS Logic
            from .utils import send_sms
            
            # Use the body directly
            # If body contains HTML (from Quill), strip tags for SMS
            import re
            clean_body = re.sub('<[^<]+?>', '', body) # Basic strip tags
            
            success, result_sid = send_sms(patient.phone, clean_body)
            
            if success:
                PatientStatus.objects.create(
                    patient=patient,
                    activity_type='SMS Sent',
                    description=f"Message: {clean_body[:50]}...",
                    full_content=clean_body
                )
                messages.success(request, f'SMS sent successfully to {patient.phone}!')
            else:
                messages.error(request, f'Failed to send SMS: {result_sid}')
        
    return redirect('patient_list')

# --- Saved Recipient (CC/BCC) CRUD ---
def recipient_list(request):
    recipients = SavedRecipient.objects.all()
    return render(request, 'birthday/recipient_list.html', {'recipients': recipients})

def recipient_create(request):
    if request.method == 'POST':
        form = SavedRecipientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recipient saved successfully!')
            return redirect('recipient_list')
    else:
        form = SavedRecipientForm()
    return render(request, 'birthday/recipient_form.html', {'form': form, 'title': 'Add New Recipient'})

def recipient_update(request, pk):
    recipient = get_object_or_404(SavedRecipient, pk=pk)
    if request.method == 'POST':
        form = SavedRecipientForm(request.POST, instance=recipient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recipient updated successfully!')
            return redirect('recipient_list')
    else:
        form = SavedRecipientForm(instance=recipient)
    return render(request, 'birthday/recipient_form.html', {'form': form, 'title': 'Edit Recipient'})

def recipient_delete(request, pk):
    recipient = get_object_or_404(SavedRecipient, pk=pk)
    if request.method == 'POST':
        recipient.delete()
        messages.success(request, 'Recipient deleted successfully!')
        return redirect('recipient_list')
    return render(request, 'birthday/recipient_confirm_delete.html', {'recipient': recipient})

def signature_list(request):
    signatures = EmailSignature.objects.all()
    return render(request, 'birthday/signature_list.html', {'signatures': signatures})

def signature_create(request):
    if request.method == 'POST':
        form = EmailSignatureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Signature created successfully!')
            return redirect('signature_list')
    else:
        form = EmailSignatureForm()
    return render(request, 'birthday/signature_form.html', {'form': form, 'title': 'Create New Signature'})

def signature_update(request, pk):
    signature = get_object_or_404(EmailSignature, pk=pk)
    if request.method == 'POST':
        form = EmailSignatureForm(request.POST, instance=signature)
        if form.is_valid():
            form.save()
            messages.success(request, 'Signature updated successfully!')
            return redirect('signature_list')
    else:
        form = EmailSignatureForm(instance=signature)
    return render(request, 'birthday/signature_form.html', {'form': form, 'title': 'Edit Signature'})

def signature_delete(request, pk):
    signature = get_object_or_404(EmailSignature, pk=pk)
    if request.method == 'POST':
        signature.delete()
        messages.success(request, 'Signature deleted successfully!')
        return redirect('signature_list')
    return render(request, 'birthday/signature_confirm_delete.html', {'signature': signature})
    return render(request, 'birthday/signature_confirm_delete.html', {'signature': signature})


def scheduled_update(request, pk):
    wish = get_object_or_404(ScheduledWish, pk=pk)
    if request.method == 'POST':
        form = ScheduledWishForm(request.POST, instance=wish)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scheduled wish updated successfully!')
            return redirect('scheduled_list')
    else:
        form = ScheduledWishForm(instance=wish)
    
    return render(request, 'birthday/schedule_form.html', {'form': form, 'is_edit': True})

def scheduled_delete(request, pk):
    wish = get_object_or_404(ScheduledWish, pk=pk)
    if request.method == 'POST':
        wish.delete()
        messages.success(request, 'Scheduled wish removed successfully!')
    return redirect('scheduled_list')

@require_POST
def scheduled_update_ajax(request, pk):
    wish = get_object_or_404(ScheduledWish, pk=pk)
    
    if wish.status != 'Pending':
        return JsonResponse({'status': 'error', 'message': 'Only pending wishes can be edited'}, status=400)
        
    custom_subject = request.POST.get('custom_subject')
    custom_body = request.POST.get('custom_body')
    cc_recipients = request.POST.get('cc_recipients')
    bcc_recipients = request.POST.get('bcc_recipients')
    scheduled_for_str = request.POST.get('scheduled_for')
    
    if custom_subject:
        wish.custom_subject = custom_subject
    if custom_body:
        wish.custom_body = custom_body
    
    wish.cc_recipients = cc_recipients or ""
    wish.bcc_recipients = bcc_recipients or ""
        
    if scheduled_for_str:
        try:
            dt = datetime.strptime(scheduled_for_str, '%Y-%m-%dT%H:%M')
            tz = pytz.timezone('America/Los_Angeles')
            wish.scheduled_for = tz.localize(dt)
        except ValueError:
            pass
            
    wish.save()
    return JsonResponse({'status': 'success', 'message': 'Wish updated successfully!'})

def get_smo_config():
    return {
        'API_KEY': os.getenv('SMO_API_KEY'),
        'BASE_URL': os.getenv('SMO_BASE_URL', 'https://smo.dentalhub.cloud'),
        'CLIENT_ID': os.getenv('SMO_CLIENT_ID', '1'),
    }

def sync_practices(request):
    config = get_smo_config()
    client_id = request.GET.get('client_id') or config['CLIENT_ID']
    
    if not config['API_KEY']:
        messages.error(request, "SMO_API_KEY not found in .env")
        return redirect('patient_list')
    
    headers = {"X-API-Key": config['API_KEY']}
    url = f"{config['BASE_URL']}/review/api/clients/{client_id}/practices"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        practices_data = data.get("practices", [])
        
        if not practices_data and isinstance(data, list):
            practices_data = data
            
        count = 0
        debug_info = ""
        for p_data in practices_data:
            p_name = p_data.get('name') or p_data.get('practice_name') or p_data.get('display_name') or 'Unknown Practice'
            p_loc = p_data.get('location') or p_data.get('city') or p_data.get('office_location') or ''
            p_ext_id = p_data.get('id') or p_data.get('pk')
            
            if not p_ext_id:
                continue

            if p_name == 'Unknown Practice' and p_data:
                debug_info = f" Keys found: {list(p_data.keys())}"

            practice, created = Practice.objects.update_or_create(
                external_id=str(p_ext_id),
                defaults={
                    'name': p_name,
                    'location': p_loc,
                    'client_id': str(client_id),
                }
            )
            count += 1
        
        success_msg = f"Successfully synced {count} practices for Client ID {client_id}."
        if debug_info:
            success_msg += debug_info
        messages.success(request, success_msg)
    except Exception as e:
        messages.error(request, f"Error syncing practices for Client ID {client_id}: {str(e)}")
        
    return redirect('patient_list')

def sync_practice_patients(request, practice_id):
    practice = get_object_or_404(Practice, pk=practice_id)
    config = get_smo_config()
    client_id = practice.client_id or config['CLIENT_ID']
    headers = {"X-API-Key": config['API_KEY']}
    
    params = {}
    if practice.last_sync:
        params['updated_since'] = practice.last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    url = f"{config['BASE_URL']}/review/api/clients/{client_id}/practices/{practice.external_id}/patients"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        patients_data = response.json().get("patients", [])
        
        created_count = 0
        updated_count = 0
        
        for p_data in patients_data:
            ext_id = str(p_data.get('id'))
            
            defaults = {
                'practice': practice,
                'first_name': p_data.get('first_name', ''),
                'last_name': p_data.get('last_name', ''),
                'email': p_data.get('email', ''),
                'phone': clean_phone_number(p_data.get('phone', '')),
                'patient_type': 'Regular',
            }
            
            dob_str = p_data.get('dob')
            if dob_str:
                try:
                    defaults['dob'] = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except:
                    pass
            
            patient, created = Patient.objects.update_or_create(
                external_id=ext_id,
                defaults=defaults
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
                
        practice.last_sync = datetime.now()
        practice.save()
        
        messages.success(request, f"Practice {practice.name}: Created {created_count}, Updated {updated_count} patients.")
    except Exception as e:
        messages.error(request, f"Error syncing patients for {practice.name}: {str(e)}")
        
    return redirect('patient_list')

def delete_practice(request, practice_id):
    practice = get_object_or_404(Practice, pk=practice_id)
    name = practice.name
    practice.delete()
    messages.success(request, f"Practice '{name}' removed successfully.")
    return redirect('patient_list')

from django.views.decorators.http import require_POST
import json

def preview_sync_patients(request, practice_id):
    practice = get_object_or_404(Practice, pk=practice_id)
    config = get_smo_config()
    client_id = practice.client_id or config['CLIENT_ID']
    headers = {"X-API-Key": config['API_KEY']}
    
    url = f"{config['BASE_URL']}/review/api/clients/{client_id}/practices/{practice.external_id}/patients"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        patients_api = data.get("patients", [])
        
        patients_with_status = []
        for p in patients_api:
            p_id = p.get('id') or p.get('patient_id')
            p_ext_id = str(p_id) if p_id else None
            p_email = (p.get('email') or p.get('email_address') or '').strip().lower()
            p_fname = (p.get('first_name') or '').strip().lower()
            p_lname = (p.get('last_name') or '').strip().lower()
            p_phone = clean_phone_number(p.get('phone') or p.get('mobile') or p.get('phone_number') or '')
            p_dob_str = p.get('date_of_birth') or p.get('dob') or p.get('birth_date') or ''
            
            # Skip patients with no birthday as requested
            if not p_dob_str:
                continue

            exists = False
            match_reason = ""

            # 1. Match by External ID
            if p_ext_id:
                if Patient.objects.filter(external_id=p_ext_id).exists():
                    exists = True
                    match_reason = "ID Match"
            
            # 2. Match by Email + Name (Prevents mixing family members sharing an email)
            if not exists and p_email:
                if Patient.objects.filter(email__iexact=p_email, first_name__iexact=p_fname).exists():
                    exists = True
                    match_reason = "Email + Name Match"
            
            # 3. Match by Name + Phone (The requested check)
            if not exists and p_phone and p_fname and p_lname:
                if Patient.objects.filter(phone=p_phone, first_name__iexact=p_fname, last_name__iexact=p_lname).exists():
                    exists = True
                    match_reason = "Phone + Name Match"
            
            # 4. Match by Name + DOB (Very reliable fallback)
            if not exists and p_fname and p_lname and p_dob_str:
                try:
                    # Try to parse API DOB
                    p_dob = None
                    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y'):
                        try:
                            p_dob = datetime.strptime(p_dob_str, fmt).date()
                            break
                        except: continue
                    
                    if p_dob and Patient.objects.filter(first_name__iexact=p_fname, last_name__iexact=p_lname, dob=p_dob).exists():
                        exists = True
                        match_reason = "Name + DOB Match"
                except:
                    pass
            
            p['exists'] = exists
            p['match_reason'] = match_reason
            patients_with_status.append(p)
            
            if "cesar" in p_fname and "munoz" in p_lname:
                print(f"DEBUG: Processing Cesar Munoz. Email: {p_email}, Phone: {p_phone}, DOB: {p_dob_str}. Match: {exists} ({match_reason})")

        # Summary Log
        matched_count = len([x for x in patients_with_status if x['exists']])
        print(f"\n--- SMO API SYNC SUMMARY ({practice.name}) ---")
        print(f"Total API records: {len(patients_with_status)}")
        print(f"Existing in system: {matched_count}")
        print("-------------------------------------------\n")

        return JsonResponse({'status': 'success', 'patients': patients_with_status})
    except Exception as e:
        import traceback
        print(f"Sync Error: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
def confirm_bulk_sync(request):
    try:
        data = json.loads(request.body)
        practice_id = data.get('practice_id')
        selected_patients = data.get('patients', [])
        
        practice = get_object_or_404(Practice, pk=practice_id)
        
        created_count = 0
        updated_count = 0
        
        updated_list = []
        created_list = []

        for p_data in selected_patients:
            # 1. Normalize and Extract data
            api_id = p_data.get('id') or p_data.get('patient_id')
            api_ext_id = str(api_id) if api_id else None
            
            p_fname = (p_data.get('first_name') or '').strip()
            p_mname = (p_data.get('middle_name') or '').strip()
            p_lname = (p_data.get('last_name') or '').strip()
            p_email = (p_data.get('email') or p_data.get('email_address') or '').strip()
            p_phone = clean_phone_number(p_data.get('phone') or p_data.get('mobile') or p_data.get('phone_number') or '')
            p_dob_str = p_data.get('date_of_birth') or p_data.get('dob') or p_data.get('birth_date') or ''
            p_gender = p_data.get('gender') or p_data.get('sex') or ''

            full_name = f"{p_fname} {p_lname}".strip()

            if not p_fname and not p_lname:
                continue

            # 2. Match with Existing Record
            existing_patient = None
            
            # Try External ID Match
            if api_ext_id and api_ext_id != 'None':
                existing_patient = Patient.objects.filter(external_id=api_ext_id).first()
            
            # Try Email + Name Match
            if not existing_patient and p_email:
                existing_patient = Patient.objects.filter(email__iexact=p_email, first_name__iexact=p_fname).first()
            
            # Try Name + Phone Match
            if not existing_patient and p_phone and p_fname and p_lname:
                existing_patient = Patient.objects.filter(
                    phone=p_phone, 
                    first_name__iexact=p_fname, 
                    last_name__iexact=p_lname
                ).first()

            # 3. Prepare the update data
            defaults = {
                'practice': practice,
                'first_name': p_fname,
                'middle_name': p_mname, # Crucial: Sync middle name to avoid 'Timothy John John Chisser'
                'last_name': p_lname,
                'email': p_email,
                'phone': p_phone,
                'gender': p_gender if p_gender in ['Male', 'Female', 'Other'] else 'Other',
                'patient_type': 'Regular',
            }

            if p_dob_str:
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y'):
                    try:
                        defaults['dob'] = datetime.strptime(p_dob_str, fmt).date()
                        break
                    except: continue

            # Final safety check: if we still don't have a DOB, skip this patient (database requires it)
            if 'dob' not in defaults:
                continue

            # 4. Save
            if existing_patient:
                # Update existing record
                for attr, value in defaults.items():
                    setattr(existing_patient, attr, value)
                if api_ext_id and api_ext_id != 'None':
                    existing_patient.external_id = api_ext_id
                existing_patient.save()
                updated_count += 1
                updated_list.append({'name': full_name, 'id': existing_patient.pk})
            else:
                # Create new record
                new_patient = Patient.objects.create(external_id=api_ext_id if api_ext_id != 'None' else None, **defaults)
                created_count += 1
                created_list.append({'name': full_name, 'id': new_patient.pk})
        
        practice.last_sync = datetime.now()
        practice.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': f"Sync Complete: {updated_count} updated, {created_count} created.",
            'updated_patients': updated_list,
            'created_patients': created_list,
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =============================================================================
# PROCEED PLAN MANAGEMENT SYSTEM - NEW VIEWS
# =============================================================================

from .models import MembershipPlan, Campaign, CampaignExecution, PracticeSettings, ServicePricing, CommunicationLog
from .forms import MembershipPlanForm, CampaignForm, PracticeSettingsForm, ServicePricingForm


# --- Membership Plans CRUD ---
def plan_list(request):
    """Display all membership plans with their details."""
    plans = MembershipPlan.objects.all()
    
    # Attach patient counts to each plan object
    for plan in plans:
        plan.patient_count = Patient.objects.filter(
            membership_plan=plan.tier,
            patient_type='Proceed'
        ).count()
    
    return render(request, 'birthday/plans/plan_list.html', {
        'plans': plans,
    })


def plan_create(request):
    """Create a new membership plan."""
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Membership plan created successfully!')
            return redirect('plan_list')
    else:
        form = MembershipPlanForm()
    
    return render(request, 'birthday/plans/plan_form.html', {
        'form': form,
        'title': 'Create New Plan',
    })


def plan_update(request, pk):
    """Update an existing membership plan."""
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f'Plan "{plan.name}" updated successfully!')
            return redirect('plan_list')
    else:
        form = MembershipPlanForm(instance=plan)
    
    return render(request, 'birthday/plans/plan_form.html', {
        'form': form,
        'plan': plan,
        'title': f'Edit {plan.name}',
    })


def plan_delete(request, pk):
    """Delete a membership plan."""
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        plan_name = plan.name
        plan.delete()
        messages.success(request, f'Plan "{plan_name}" deleted successfully!')
        return redirect('plan_list')
    
    return render(request, 'birthday/plans/plan_confirm_delete.html', {'plan': plan})


# --- Service Pricing CRUD ---
def service_list(request):
    """Display all services with pricing across plans."""
    services = ServicePricing.objects.filter(is_active=True)
    categories = ServicePricing.CATEGORY_CHOICES
    
    # Group services by category
    services_by_category = {}
    for cat_code, cat_name in categories:
        services_by_category[cat_name] = services.filter(category=cat_code)
    
    return render(request, 'birthday/services/service_list.html', {
        'services': services,
        'services_by_category': services_by_category,
        'categories': categories,
    })


def service_create(request):
    """Create a new service."""
    if request.method == 'POST':
        form = ServicePricingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service created successfully!')
            return redirect('service_list')
    else:
        form = ServicePricingForm()
    
    return render(request, 'birthday/services/service_form.html', {
        'form': form,
        'title': 'Add New Service',
    })


def service_update(request, pk):
    """Update an existing service."""
    service = get_object_or_404(ServicePricing, pk=pk)
    if request.method == 'POST':
        form = ServicePricingForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f'Service "{service.name}" updated successfully!')
            return redirect('service_list')
    else:
        form = ServicePricingForm(instance=service)
    
    return render(request, 'birthday/services/service_form.html', {
        'form': form,
        'service': service,
        'title': f'Edit {service.name}',
    })


def service_delete(request, pk):
    """Delete a service."""
    service = get_object_or_404(ServicePricing, pk=pk)
    if request.method == 'POST':
        service_name = service.name
        service.delete()
        messages.success(request, f'Service "{service_name}" deleted successfully!')
        return redirect('service_list')
    
    return render(request, 'birthday/services/service_confirm_delete.html', {'service': service})


# --- Campaigns CRUD ---
def campaign_list(request):
    """Display all campaigns with their status and stats."""
    campaigns = Campaign.objects.all()
    
    return render(request, 'birthday/campaigns/campaign_list.html', {
        'campaigns': campaigns,
    })


def campaign_create(request):
    """Create a new campaign."""
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            # Handle target_plans as JSON
            target_plans = request.POST.getlist('target_plans')
            campaign.target_plans = target_plans if target_plans else []
            campaign.save()
            messages.success(request, 'Campaign created successfully!')
            return redirect('campaign_list')
    else:
        form = CampaignForm()
    
    return render(request, 'birthday/campaigns/campaign_form.html', {
        'form': form,
        'title': 'Create New Campaign',
    })


def campaign_update(request, pk):
    """Update an existing campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            updated_campaign = form.save(commit=False)
            target_plans = request.POST.getlist('target_plans')
            updated_campaign.target_plans = target_plans if target_plans else []
            updated_campaign.save()
            messages.success(request, f'Campaign "{campaign.name}" updated successfully!')
            return redirect('campaign_list')
    else:
        form = CampaignForm(instance=campaign)
    
    return render(request, 'birthday/campaigns/campaign_form.html', {
        'form': form,
        'campaign': campaign,
        'title': f'Edit {campaign.name}',
    })


def campaign_delete(request, pk):
    """Delete a campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        campaign_name = campaign.name
        campaign.delete()
        messages.success(request, f'Campaign "{campaign_name}" deleted successfully!')
        return redirect('campaign_list')
    
    return render(request, 'birthday/campaigns/campaign_confirm_delete.html', {'campaign': campaign})


@require_POST
def campaign_run(request, pk):
    """Manually run a campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)
    
    # Get eligible patients based on trigger type
    today = date.today()
    patients = Patient.objects.filter(patient_type='Proceed')
    
    # Filter by target plans if specified
    if campaign.target_plans:
        patients = patients.filter(membership_plan__in=campaign.target_plans)
    
    # Filter by patient type if specified
    if campaign.target_patient_type:
        patients = patients.filter(patient_type=campaign.target_patient_type)
    
    targeted_patients = []
    
    if campaign.trigger_type == 'birthday':
        # Today's birthdays
        targeted_patients = patients.filter(
            dob__month=today.month,
            dob__day=today.day
        )
    elif campaign.trigger_type == 'birthday_before':
        # Birthdays X days from now
        target_date = today + timedelta(days=campaign.days_before)
        targeted_patients = patients.filter(
            dob__month=target_date.month,
            dob__day=target_date.day
        )
    elif campaign.trigger_type in ['expiring_30', 'expiring_14', 'expiring_7']:
        # Expiring plans
        days_map = {'expiring_30': 30, 'expiring_14': 14, 'expiring_7': 7}
        target_days = days_map[campaign.trigger_type]
        target_date = today + timedelta(days=target_days)
        
        targeted_patients = []
        for patient in patients.filter(enrollment_date__isnull=False):
            expiry = patient.enrollment_date + timedelta(days=365)
            if expiry == target_date:
                targeted_patients.append(patient)
    elif campaign.trigger_type == 'expired':
        # Just expired (within last 7 days)
        for patient in patients.filter(enrollment_date__isnull=False):
            expiry = patient.enrollment_date + timedelta(days=365)
            if today <= (expiry + timedelta(days=7)) and today > expiry:
                targeted_patients.append(patient)
    elif campaign.trigger_type == 'upgrade_promo':
        # Bronze and Silver members (for Gold upgrade promotion)
        targeted_patients = patients.filter(membership_plan__in=['Bronze', 'Silver'])
    
    # Log the execution
    emails_sent = 0
    sms_sent = 0
    errors = 0
    
    # For now, just count - actual sending would be implemented later
    patient_count = len(targeted_patients) if isinstance(targeted_patients, list) else targeted_patients.count()
    
    CampaignExecution.objects.create(
        campaign=campaign,
        patients_targeted=patient_count,
        emails_sent=emails_sent,
        sms_sent=sms_sent,
        errors=errors,
        notes=f"Manual run - {patient_count} patients targeted"
    )
    
    campaign.total_sent += patient_count
    campaign.last_run = datetime.now()
    campaign.save()
    
    return JsonResponse({
        'status': 'success',
        'message': f'Campaign run complete! {patient_count} patients targeted.',
        'patients_targeted': patient_count,
    })


# --- Practice Settings ---
def practice_settings(request):
    """Manage practice settings (singleton)."""
    settings = PracticeSettings.get_settings()
    
    if request.method == 'POST':
        form = PracticeSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings saved successfully!')
            return redirect('practice_settings')
    else:
        form = PracticeSettingsForm(instance=settings)
    
    return render(request, 'birthday/settings/practice_settings.html', {
        'form': form,
        'settings': settings,
    })


# --- Analytics Dashboard ---
def analytics_dashboard(request):
    """Comprehensive analytics dashboard."""
    today = date.today()
    
    # Basic counts
    total_patients = Patient.objects.count()
    proceed_patients = Patient.objects.filter(patient_type='Proceed').count()
    regular_patients = Patient.objects.filter(patient_type='Regular').count()
    
    # Plan distribution
    gold_count = Patient.objects.filter(membership_plan='Gold', patient_type='Proceed').count()
    silver_count = Patient.objects.filter(membership_plan='Silver', patient_type='Proceed').count()
    bronze_count = Patient.objects.filter(membership_plan='Bronze', patient_type='Proceed').count()
    
    # Status breakdown
    active_count = 0
    expiring_soon_count = 0
    expired_count = 0
    
    proceed_patients_qs = Patient.objects.filter(patient_type='Proceed', enrollment_date__isnull=False)
    for patient in proceed_patients_qs:
        progress = patient.plan_progress
        if progress['is_expired']:
            expired_count += 1
        elif progress['days_left'] <= 30:
            expiring_soon_count += 1
        else:
            active_count += 1
    
    # Today's birthdays
    todays_birthdays = Patient.objects.filter(
        dob__month=today.month,
        dob__day=today.day
    )
    
    # This week's birthdays
    week_end = today + timedelta(days=7)
    upcoming_birthdays = Patient.objects.filter(
        dob__month__gte=today.month,
        dob__day__gte=today.day,
        dob__day__lte=week_end.day
    )[:10]
    
    # Recent activity
    recent_patients = Patient.objects.order_by('-updated_at')[:5]
    
    # Campaign stats
    active_campaigns = Campaign.objects.filter(is_active=True).count()
    total_campaign_sends = Campaign.objects.aggregate(total=Sum('total_sent'))['total'] or 0
    
    # Plan history (last 30 days)
    from .models import PlanHistory
    thirty_days_ago = today - timedelta(days=30)
    upgrades = PlanHistory.objects.filter(
        change_type='Upgrade',
        created_at__gte=thirty_days_ago
    ).count()
    downgrades = PlanHistory.objects.filter(
        change_type='Downgrade',
        created_at__gte=thirty_days_ago
    ).count()
    renewals = PlanHistory.objects.filter(
        change_type='Renewal',
        created_at__gte=thirty_days_ago
    ).count()
    
    context = {
        'total_patients': total_patients,
        'proceed_patients': proceed_patients,
        'regular_patients': regular_patients,
        'gold_count': gold_count,
        'silver_count': silver_count,
        'bronze_count': bronze_count,
        'active_count': active_count,
        'expiring_soon_count': expiring_soon_count,
        'expired_count': expired_count,
        'todays_birthdays': todays_birthdays,
        'upcoming_birthdays': upcoming_birthdays,
        'recent_patients': recent_patients,
        'active_campaigns': active_campaigns,
        'total_campaign_sends': total_campaign_sends,
        'upgrades': upgrades,
        'downgrades': downgrades,
        'renewals': renewals,
    }
    
    return render(request, 'birthday/analytics/analytics_dashboard.html', context)


# --- Communication Logs ---
def communication_log_list(request):
    """Display communication history for all patients."""
    from django.core.paginator import Paginator
    
    logs = CommunicationLog.objects.all().select_related('patient', 'campaign')
    
    # Filters
    channel = request.GET.get('channel', '')
    status = request.GET.get('status', '')
    
    if channel:
        logs = logs.filter(channel=channel)
    if status:
        logs = logs.filter(status=status)
    
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'birthday/communications/communication_log_list.html', {
        'page_obj': page_obj,
        'channel': channel,
        'status': status,
    })
