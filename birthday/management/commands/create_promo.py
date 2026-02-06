from django.core.management.base import BaseCommand
from birthday.models import Campaign, MessageTemplate, EmailSignature

class Command(BaseCommand):
    help = 'Creates the Proceed Plan promotion campaign'

    def handle(self, *args, **options):
        # 1. Signature
        sig, _ = EmailSignature.objects.get_or_create(
            name="Default Signature",
            defaults={
                'content': 'Best Regards,<br>Proceed Dental',
                'is_default': True
            }
        )

        # 2. Template
        template, created = MessageTemplate.objects.get_or_create(
            name="Proceed Plan Promotion",
            defaults={
                'type': 'Email',
                'subject': 'Start Saving on Your Dental Care Today!',
                'body': 'Hi {first_name},\n\nWe noticed you haven\'t joined our Proceed Dental Savings Plan yet. Our members save significantly on preventative care and other treatments.\n\nCheck out our plans here: http://127.0.0.1:8002/plans/',
                'signature': sig
            }
        )

        # 3. Campaign (FORCE CREATE with unique name if needed, but get_or_create is fine)
        campaign, created = Campaign.objects.get_or_create(
            name="Promote Proceed Plan to Regulars",
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
            self.stdout.write(self.style.SUCCESS(f'Successfully created campaign: {campaign.name}'))
        else:
            # Ensure it targets Regulars
            campaign.target_patient_type = 'Regular'
            campaign.trigger_type = 'manual'
            campaign.save()
            self.stdout.write(self.style.WARNING(f'Campaign "{campaign.name}" already existed, updated target to Regular.'))

        # List all to be sure
        self.stdout.write("Current Campaign List:")
        for c in Campaign.objects.all():
            self.stdout.write(f"- {c.name} ({c.trigger_type}) Status: {'Active' if c.is_active else 'Inactive'}")
