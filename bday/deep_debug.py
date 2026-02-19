import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
django.setup()

from birthday.models import Patient, PatientStatus, ScheduledWish

patients = Patient.objects.filter(first_name='Bijoy', last_name='Krishna')
for p in patients:
    print(f"\n=== Patient: {p.first_name} {p.last_name} (ID: {p.id}) ===")
    activities = PatientStatus.objects.filter(patient=p).order_by('-created_at')
    print(f"Activities ({activities.count()}):")
    for a in activities:
        print(f"  - {a.activity_type} | {a.description} | {a.created_at}")
    
    wishes = ScheduledWish.objects.filter(patient=p).order_by('-scheduled_for')
    print(f"Scheduled Wishes ({wishes.count()}):")
    for w in wishes:
        print(f"  - Sched: {w.scheduled_for} | Status: {w.status} | Sent at: {w.sent_at}")
