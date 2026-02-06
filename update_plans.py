from birthday.models import MembershipPlan, PracticeSettings, ServicePricing
from django.db import transaction

@transaction.atomic
def update_membership_plans():
    # 1. Update/Create Practice Settings
    settings = PracticeSettings.get_settings()
    settings.reinstatement_fee = 50.00
    settings.save()
    print("Updated Practice Settings.")

    # 2. Update/Create Membership Plans
    plans_data = [
        {
            'name': 'Proceed Bronze',
            'tier': 'Bronze',
            'annual_price': 350.00,
            'description': 'Essential coverage for preventive care and basic savings.',
            'included_services': [
                'Comprehensive Exam', 'Recall Exam', 'Emergency Exam',
                'Periapical X-rays', 'Bitewing X-rays', 
                '2 Preventive Cleanings', '2 Fluoride Treatments'
            ],
            'preventive_discount': 5,
            'restorative_discount': 5,
            'cosmetic_discount': 5,
            'implant_discount': 0,
            'color': '#CD7F32',
            'icon': 'bi-award',
            'display_order': 1,
        },
        {
            'name': 'Proceed Silver',
            'tier': 'Silver',
            'annual_price': 550.00,
            'description': 'Enhanced coverage including CT scans and higher savings on advanced care.',
            'included_services': [
                'Comprehensive Exam', 'Recall Exam', 'Emergency Exam',
                'Periapical X-rays', 'Bitewing X-rays', 'CT Scan',
                '2 Preventive Cleanings', '2 Fluoride Treatments'
            ],
            'preventive_discount': 10,
            'restorative_discount': 10,
            'cosmetic_discount': 10,
            'implant_discount': 5,
            'color': '#C0C0C0',
            'icon': 'bi-gem',
            'display_order': 2,
            'is_featured': True,
        },
        {
            'name': 'Proceed Gold',
            'tier': 'Gold',
            'annual_price': 750.00,
            'description': 'Premium coverage with maximum savings on all dental services including implants.',
            'included_services': [
                'Comprehensive Exam', 'Recall Exam', 'Emergency Exam',
                'Periapical X-rays', 'Bitewing X-rays', 'CT Scan',
                '2 Preventive Cleanings', '2 Fluoride Treatments'
            ],
            'preventive_discount': 15,
            'restorative_discount': 15,
            'cosmetic_discount': 15,
            'implant_discount': 10,
            'color': '#FFD700',
            'icon': 'bi-star-fill',
            'display_order': 3,
        }
    ]

    for data in plans_data:
        plan, created = MembershipPlan.objects.update_or_create(
            tier=data['tier'],
            defaults=data
        )
        status = "Created" if created else "Updated"
        print(f"{status} {plan.tier} plan.")

    # 3. Seed some Service Pricing data based on the website
    services_data = [
        # Preventive
        ('Comprehensive Exam', 'Preventive', 150.00, True, True, True),
        ('Recall Exam', 'Preventive', 80.00, True, True, True),
        ('Emergency Exam', 'Preventive', 120.00, True, True, True),
        ('CT Scan', 'Preventive', 350.00, False, True, True),
        ('Adult Cleaning', 'Preventive', 120.00, True, True, True),
        ('Child Cleaning', 'Preventive', 90.00, True, True, True),
        ('Fluoride Treatment', 'Preventive', 45.00, True, True, True),
        
        # Restorative
        ('Scaling and Root Planing', 'Restorative', 250.00, False, False, False),
        ('Composite Filling', 'Restorative', 200.00, False, False, False),
        ('Dental Crown', 'Restorative', 1200.00, False, False, False),
        ('Root Canal', 'Restorative', 1000.00, False, False, False),
        
        # Implant
        ('Dental Implant', 'Implant', 2500.00, False, False, False),
        ('Socket Grafting', 'Implant', 600.00, False, False, False),
    ]

    # Clear existing services to avoid duplicates during this update
    ServicePricing.objects.all().delete()
    
    for name, category, price, in_b, in_s, in_g in services_data:
        ServicePricing.objects.create(
            name=name,
            category=category,
            regular_price=price,
            included_in_bronze=in_b,
            included_in_silver=in_s,
            included_in_gold=in_g
        )
    print("Seeded basic service pricing.")

if __name__ == "__main__":
    update_membership_plans()
