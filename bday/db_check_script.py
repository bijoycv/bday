
import os
import django
import sys

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
    django.setup()
    from birthday.models import Campaign
    count = Campaign.objects.count()
    with open('db_check.txt', 'w') as f:
        f.write(f"Campaign count: {count}\n")
        f.write("Campaigns:\n")
        for c in Campaign.objects.all():
            f.write(f"- {c.name}\n")
except Exception as e:
    with open('db_check.txt', 'w') as f:
        f.write(f"Error: {str(e)}\n")
