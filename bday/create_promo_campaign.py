from birthday.models import Campaign, MessageTemplate, EmailSignature
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
django.setup()

def create_promo_campaign():
    # 1. Get or create signature
    sig, _ = EmailSignature.objects.get_or_create(
        name="Default Signature",
        defaults={
            'content': 'Best Regards,<br>Proceed Dental',
            'is_default': True
        }
    )

    # 2. Get or create template
    template_name = "Proceed Plan Promotion"
    template, created = MessageTemplate.objects.get_or_create(
        name=template_name,
        defaults={
            'type': 'Email',
            'subject': 'Start Saving on Your Dental Care Today!',
            'body': 'Hi {first_name},\n\nWe noticed you haven\'t joined our Proceed Dental Savings Plan yet. Our members save significantly on preventative care and other treatments.\n\nCheck out our plans here: http://127.0.0.1:8002/plans/',
            'signature': sig
        }
    )

    # 3. Create Campaign
    campaign_name = "Promote Proceed Plan to Regulars"
    campaign, created = Campaign.objects.get_or_create(
        name=campaign_name,
        defaults={
            'trigger_type': 'manual',
            'description': 'Promotional campaign to convert regular patients to Proceed Dental Savings Plan members.',
            'target_patient_type': 'Regular',
            'channel': 'Email',
            'email_template': template,
            'is_active': False
        }
    )

    if created:
        print(f"Successfully created campaign: {campaign_name}")
    else:
        print(f"Campaign already exists: {campaign_name}")
        # Update it just in case to ensure it matches expectations
        campaign.target_patient_type = 'Regular'
        campaign.trigger_type = 'manual'
        campaign.save()
        print("Updated existing campaign settings.")

if __name__ == "__main__":
    create_promo_campaign()
    print("All campaigns in DB:")
    for c in Campaign.objects.all():
        print(f"- {c.name} ({c.trigger_type}) targets {c.target_patient_type}")
