
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
django.setup()

from birthday.models import MessageTemplate, Campaign

campaigns_data = [
    {
        'name': "Valentine’s Day - Love Your Smile",
        'description': "Plan signup + cosmetic add-on promotion for Valentine's Day.",
        'trigger_type': 'manual',
        'target_patient_type': 'Regular',
        'email_subject': "❤️ Love Your Smile this Valentine's Day!",
        'email_body': """<p>Hi {first_name},</p>
<p>This Valentine’s Day, fall in love with your smile! 😍</p>
<p>We believe everyone deserves a smile they can be proud of. That's why we're offering a special <strong>Love Your Smile</strong> promotion:</p>
<ul>
    <li>Join our <strong>Proceed Dental Savings Plan</strong> and get 50% OFF professional teeth whitening!</li>
    <li>Already a member? Refer a friend and you both get a special gift.</li>
</ul>
<p>Freedom from expensive insurance and hidden costs is just a click away.</p>
<p>Love,</p>
<p>The Team at Proceed Dental</p>""",
        'sms_body': "Hi {first_name}, love your smile this Valentine's! Join our Proceed Plan today and get 50% off professional whitening. Reply for details!"
    },
    {
        'name': "Easter - Spring Cleaning",
        'description': "Family checkup push for Spring.",
        'trigger_type': 'manual',
        'email_subject': "🐰 Spring Cleaning for Your Smile!",
        'email_body': """<p>Hi {first_name},</p>
<p>Spring is here, and it's the perfect time for a fresh start! 🌷</p>
<p>Don't forget to schedule your family's <strong>Spring Cleaning</strong>. Regular checkups are the best way to keep your smiles bright and healthy all year long.</p>
<p>Special Easter Bonus: Every child seen this month gets a special tooth-friendly surprise!</p>
<p>See you soon!</p>""",
        'sms_body': "Hi {first_name}, spring is here! 🌷 Time for a fresh smile. Schedule your family's spring cleaning today and get a special Easter surprise for the kids!"
    },
    {
        'name': "Mother’s Day - Mom’s Smile Week",
        'description': "Giftable membership / family enrollment promotion.",
        'trigger_type': 'manual',
        'email_subject': "🌸 A Smile as Bright as Mom's",
        'email_body': """<p>Hi {first_name},</p>
<p>Show Mom how much you care with a gift that lasts a lifetime! 💖</p>
<p>This Mother's Day, we're offering <strong>Giftable Membership Plans</strong>. It's the perfect way to ensure your loved ones have access to high-quality dental care without the stress of insurance.</p>
<p>Give her the gift of health and confidence.</p>
<p>Happy Mother's Day!</p>""",
        'sms_body': "Hi {first_name}, give Mom the gift of a beautiful smile! 🌸 Giftable membership plans are now available. Reply to learn more!"
    },
    {
        'name': "Memorial Day - Smile Into Summer",
        'description': "Preventive reminder + membership drive.",
        'trigger_type': 'manual',
        'email_subject': "🇺🇸 Smile Into Summer!",
        'email_body': """<p>Hi {first_name},</p>
<p>Kick off summer with a healthy smile! ☀️</p>
<p>As we honor this Memorial Day, we're reminded of the importance of health and community. Don't let your dental benefits go to waste—schedule your summer checkup today!</p>
<p>Not a member yet? Join our Proceed Plan now and secure your summer savings.</p>
<p>Have a safe and happy holiday!</p>""",
        'sms_body': "Hi {first_name}, kick off summer with a healthy smile! ☀️ Schedule your summer checkup today. Not a member? Join Proceed for instant savings!"
    },
    {
        'name': "Independence Day - Freedom from Surprise Bills",
        'description': "Proceed Plan CTA for Independence Day.",
        'trigger_type': 'manual',
        'target_patient_type': 'Regular',
        'email_subject': "🎆 Freedom from Surprise Dental Bills!",
        'email_body': """<p>Hi {first_name},</p>
<p>Celebrate your independence from hidden dental costs! 🎆</p>
<p>Tired of high insurance premiums and surprise bills? Our <strong>Proceed Savings Plan</strong> gives you the freedom to choose your care with transparent, upfront pricing.</p>
<p>Join today and celebrate true smile freedom!</p>""",
        'sms_body': "Hi {first_name}, celebrate freedom from surprise dental bills! 🎆 Join our transparent Proceed Savings Plan today and save big. Click here: [link]"
    },
    {
        'name': "Labor Day - Back to Routine",
        'description': "Reactivation + family enrollment promotion.",
        'trigger_type': 'manual',
        'email_subject': "🛠️ Back to Routine, Back to Health!",
        'email_body': """<p>Hi {first_name},</p>
<p>As summer winds down, it's time to get back to routine! 🛠️</p>
<p>School is starting and schedules are filling up. Make sure your family's dental health is on the list. We're offering a special <strong>Labor Day Enrollment Bonus</strong> for new family plans.</p>
<p>Schedule your checkup today!</p>""",
        'sms_body': "Hi {first_name}, back to school, back to routine! 🛠️ Secure your family's dental health for the season. Special enrollment bonuses available now!"
    },
    {
        'name': "Halloween - Cavity-Free Halloween",
        'description': "Kids + fluoride highlight for Halloween.",
        'trigger_type': 'manual',
        'email_subject': "🎃 Don't Let the Treats Trick Your Teeth!",
        'email_body': """<p>Hi {first_name},</p>
<p>Happy Halloween! 🎃 Don't let the sticky treats play tricks on your teeth.</p>
<p>We're highlighting our <strong>Kids' Fluoride Treatments</strong> this month to keep those young smiles strong against the candy onslaught.</p>
<p>Ask us about our Halloween Cavity-Safe tips at your next visit!</p>""",
        'sms_body': "Happy Halloween {first_name}! 🎃 Don't let the treats trick your teeth. Schedule a fluoride treatment for the kids today and keep smiles strong!"
    },
    {
        'name': "Thanksgiving - Thankful for Smiles",
        'description': "Year-end preventive reminder.",
        'trigger_type': 'manual',
        'email_subject': "🦃 Thankful for Your Smile",
        'email_body': """<p>Hi {first_name},</p>
<p>We are truly thankful for you! 🦃</p>
<p>As the year comes to a close, we want to make sure you've used your preventive benefits. Don't leave your health for next year—schedule your final cleaning of 2026 today.</p>
<p>Wishing you a wonderful Thanksgiving!</p>""",
        'sms_body': "Hi {first_name}, we're thankful for you! 🦃 Use your 2026 benefits before they expire. Schedule your year-end cleaning today!"
    }
]

for data in campaigns_data:
    # Create Email Template
    email_tpl, created = MessageTemplate.objects.get_or_create(
        name=f"Campaign: {data['name']} (Email)",
        defaults={
            'type': 'Email',
            'subject': data['email_subject'],
            'body': data['email_body']
        }
    )
    
    # Create SMS Template
    sms_tpl, created = MessageTemplate.objects.get_or_create(
        name=f"Campaign: {data['name']} (SMS)",
        defaults={
            'type': 'SMS',
            'body': data['sms_body']
        }
    )
    
    # Create Campaign
    Campaign.objects.get_or_create(
        name=data['name'],
        defaults={
            'description': data['description'],
            'trigger_type': data['trigger_type'],
            'target_patient_type': data.get('target_patient_type'),
            'channel': 'Both',
            'email_template': email_tpl,
            'sms_template': sms_tpl,
            'is_active': False  # Always inactive by default as requested
        }
    )

print("Successfully created holiday campaigns and templates.")
