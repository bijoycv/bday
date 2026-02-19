import os
import django
import pytz
from datetime import datetime, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
django.setup()

from birthday.models import PatientStatus, ScheduledWish
from django.utils import timezone

today = timezone.localdate()
start = timezone.make_aware(datetime.combine(today, time.min))
print(f"Server Time: {datetime.now()}")
print(f"Local Date: {today}")
print(f"Start of Day (PST): {start}")

activities = PatientStatus.objects.filter(
    activity_type__in=['Email Sent', 'SMS Sent'],
    created_at__gte=start
).order_by('-created_at')

print(f"\n--- SUCCESSFUL ACTIVITIES TODAY ({activities.count()}) ---")
for a in activities:
    print(f"- {a.patient.first_name} {a.patient.last_name} | {a.activity_type} | Sent at: {a.created_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")

wishes = ScheduledWish.objects.filter(
    sent_at__gte=start
).order_by('-sent_at')

print(f"\n--- SCHEDULED WISHES SENT TODAY ({wishes.count()}) ---")
for w in wishes:
    print(f"- {w.patient} | Status: {w.status} | Sent at: {w.sent_at.strftime('%Y-%m-%d %H:%M:%S %Z') if w.sent_at else 'N/A'}")
