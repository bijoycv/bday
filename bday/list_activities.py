import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
django.setup()
from birthday.models import PatientStatus
from django.utils import timezone
from datetime import datetime, time

today = timezone.localdate()
start = timezone.make_aware(datetime.combine(today, time.min))
activities = PatientStatus.objects.filter(activity_type__in=['Email Sent', 'SMS Sent'], created_at__gte=start).order_by('-created_at')

print("ID | Patient | Time | Description")
for a in activities:
    print(f"{a.id} | {a.patient} | {a.created_at} | {a.description}")
