from django.core.management.base import BaseCommand
from birthday.models import Campaign, MessageTemplate, EmailSignature

class Command(BaseCommand):
    help = 'Creates best converyable holiday campaigns for special days'

    def handle(self, *args, **options):
        # 1. Signature
        sig, _ = EmailSignature.objects.get_or_create(
            name="Default Signature",
            defaults={
                'content': 'Best Regards,<br>Proceed Dental',
                'is_default': True
            }
        )

        holidays = [
            {
                'name': "Valentine’s Day — Love Your Smile",
                'subject': "❤️ Love Your Smile this Valentine's Day!",
                'body': "Hi {first_name},\n\nValentine's is almost here! Treat yourself to the smile you deserve. Join our Proceed Dental Savings Plan today and get exclusive access to member-only savings on cosmetic treatments like professional whitening. Love your smile as much as we do!\n\nSign up here: http://127.0.0.1:8002/plans/",
                'description': "Valentine's Day (Feb 14) — Love Your Smile (plan signup + cosmetic add-on)",
                'target': 'Regular'
            },
            {
                'name': "Easter — Spring Cleaning for Your Smile",
                'subject': "🐰 Hop in for a Spring Cleaning!",
                'body': "Hi {first_name},\n\nSpring is a time for renewal! Bring the whole family in for a \"Spring Cleaning\" checkup. Our Proceed Dental Savings Plan makes it easy and affordable for everyone to keep their pearly whites healthy. Schedule your family's visit today and start saving!\n\nCheck out our family plans: http://127.0.0.1:8002/plans/",
                'description': "Easter (Apr 5) — Spring Cleaning for Your Smile (family checkup push)",
                'target': 'Regular'
            },
            {
                'name': "Mother’s Day — Mom’s Smile Week",
                'subject': "💐 A Gift Mom Will Truly Value",
                'body': "Hi {first_name},\n\nThis Mother's Day, give Mom the gift of a healthy smile. Enroll her in our Proceed Dental Savings Plan or sign up for a family membership to ensure everyone stays protected. She's always looking out for you—now you can look out for her!\n\nExplore membership options: http://127.0.0.1:8002/plans/",
                'description': "Mother’s Day (May 10) — Mom’s Smile Week (giftable membership / family enrollment)",
                'target': 'Regular'
            },
            {
                'name': "Memorial Day — Smile Into Summer",
                'subject': "☀️ Smile Into Summer!",
                'body': "Hi {first_name},\n\nMemorial Day kicks off the summer season! Don't let your dental health take a vacation. It's the perfect time to catch up on preventive care or join our Proceed Dental Savings Plan to avoid unexpected bills during your summer adventures.\n\nStart your summer with savings: http://127.0.0.1:8002/plans/",
                'description': "Memorial Day (May 25) — Smile Into Summer (preventive reminder + membership drive)",
                'target': None
            },
            {
                'name': "Independence Day — Freedom from Toothaches",
                'subject': "🇺🇸 Freedom From Surprise Dental Bills",
                'body': "Hi {first_name},\n\nCelebrate your independence—including freedom from the stress of surprise dental costs! Our Proceed Dental Savings Plan gives you transparent pricing and predictable savings on every visit. Join today and smile with confidence!\n\nJoin the plan: http://127.0.0.1:8002/plans/",
                'description': "Independence Day (Jul 3 observed) — Freedom from surprise dental bills (plan CTA)",
                'target': 'Regular'
            },
            {
                'name': "Labor Day — Back to Routine",
                'subject': "📝 Back to Routine, Back to Healthy Smiles",
                'body': "Hi {first_name},\n\nAs summer winds down and routines return, don't forget your dental health! Labor Day is a great reminder to schedule those family checkups. Reactivate your membership or join today to keep your family's smiles on track for the new season.\n\nSchedule now: http://127.0.0.1:8002/plans/",
                'description': "Labor Day (Sep 7) — Back to Routine (reactivation + family enrollment)",
                'target': None
            },
            {
                'name': "Halloween — Cavity-Free Halloween",
                'subject': "🎃 Wishing You a Cavity-Free Halloween!",
                'body': "Hi {first_name},\n\nTreats are everywhere this time of year! Keep your kids' smiles safe with a fluoride treatment and a post-Halloween checkup. Our Proceed Dental Savings Plan covers preventive care so you can focus on the fun, not the cavities!\n\nProtect their smiles: http://127.0.0.1:8002/plans/",
                'description': "Halloween (Oct 31) — Cavity-Free Halloween (kids + fluoride highlight)",
                'target': None
            },
            {
                'name': "Thanksgiving — Thankful for Smiles",
                'subject': "🦃 We're Thankful for Your Smile!",
                'body': "Hi {first_name},\n\nAs the year ends, we want to express our gratitude for being part of our dental family. Now is a great time to use your remaining preventive benefits or join our Proceed Dental Savings Plan to start the new year with a healthy, happy smile!\n\nSee our plans: http://127.0.0.1:8002/plans/",
                'description': "Thanksgiving (Nov 26) — Thankful for Smiles (year-end preventive reminder)",
                'target': None
            },
        ]

        for holiday in holidays:
            # Create Template
            template, t_created = MessageTemplate.objects.get_or_create(
                name=holiday['name'] + " Template",
                defaults={
                    'type': 'Email',
                    'subject': holiday['subject'],
                    'body': holiday['body'],
                    'signature': sig
                }
            )
            
            # Create Campaign
            campaign, c_created = Campaign.objects.get_or_create(
                name=holiday['name'],
                defaults={
                    'trigger_type': 'manual',
                    'description': holiday['description'],
                    'target_patient_type': holiday['target'],
                    'channel': 'Email',
                    'email_template': template,
                    'is_active': False
                }
            )
            
            # Update if already exists to ensure content is fresh
            if not c_created:
                campaign.email_template = template
                campaign.description = holiday['description']
                campaign.target_patient_type = holiday['target']
                campaign.save()

            status = "Created" if c_created else "Updated"
            self.stdout.write(self.style.SUCCESS(f'{status} holiday campaign: {campaign.name}'))

        self.stdout.write(self.style.SUCCESS('All holiday campaigns processed successfully.'))
