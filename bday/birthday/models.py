from django.db import models

def clean_phone_number(phone):
    """Standardize phone number to 10 digits."""
    if not phone:
        return ""
    # Remove all non-digit characters
    cleaned = "".join(filter(str.isdigit, str(phone)))
    # If it starts with 1 and is 11 digits, strip the leading 1
    if len(cleaned) == 11 and cleaned.startswith("1"):
        cleaned = cleaned[1:]
    return cleaned[:10]

class Practice(models.Model):
    external_id = models.IntegerField(unique=True, verbose_name="SMO Practice ID")
    client_id = models.CharField(max_length=50, default="1", verbose_name="SMO Client ID")
    name = models.CharField(max_length=200, verbose_name="Practice Name")
    location = models.CharField(max_length=200, blank=True, null=True)
    last_sync = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Patient(models.Model):
    external_id = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name="External ID (SMO)")
    practice = models.ForeignKey(Practice, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Middle Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    dob = models.DateField(verbose_name="Date of Birth")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    email = models.EmailField(verbose_name="Email Address")
    address = models.TextField(blank=True, null=True, verbose_name="Street Address")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="City")
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name="State")
    zip_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Zip Code")
    
    # New fields for more detailed data
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Gender")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    
    # Optional fields based on the input file
    PATIENT_TYPE_CHOICES = [
        ('Regular', 'Regular'),
        ('Proceed', 'Proceed (In-house Plan)'),
    ]
    patient_type = models.CharField(max_length=20, choices=PATIENT_TYPE_CHOICES, default='Regular', verbose_name="Patient Type")
    MEMBERSHIP_PLAN_CHOICES = [
        ('Gold', 'Gold'),
        ('Silver', 'Silver'),
        ('Bronze', 'Bronze'),
    ]
    membership_plan = models.CharField(max_length=20, choices=MEMBERSHIP_PLAN_CHOICES, blank=True, null=True, verbose_name="Membership Plan")
    
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Credit Card', 'Credit Card'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True, verbose_name="Payment Method")
    
    enrollment_date = models.DateField(blank=True, null=True, verbose_name="Enrollment Date")
    is_verified = models.BooleanField(default=False, verbose_name="Verified")
    
    # Opt-out fields
    accepts_marketing = models.BooleanField(default=True, verbose_name="Accepts Communications")
    unsubscribe_reason = models.TextField(blank=True, null=True, verbose_name="Unsubscribe Reason")
    unsubscribed_at = models.DateTimeField(blank=True, null=True, verbose_name="Unsubscribed Date")

    # payment_amount was replaced by payment_method as per requirements for Cash/Credit Card standardization
    # payment_amount = models.CharField(max_length=50, blank=True, null=True, verbose_name="Payment Amount")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def plan_progress(self):
        """Calculate the progress of the 1-year plan with descriptive labels."""
        from datetime import date
        if not self.enrollment_date:
            return {
                'percentage': 0, 
                'is_expired': False, 
                'days_left': 0, 
                'status': 'secondary',
                'label': 'No Plan'
            }
        
        today = date.today()
        elapsed = (today - self.enrollment_date).days
        total_days = 365
        
        percentage = min(max(int((elapsed / total_days) * 100), 0), 100)
        is_expired = elapsed > total_days
        days_left = max(total_days - elapsed, 0)
        
        from datetime import timedelta
        expiry_date = self.enrollment_date + timedelta(days=365)
        
        # Determine status, color and label
        if is_expired:
            status = 'danger'
            # expired for less than 30 days
            if (elapsed - total_days) <= 30:
                label = 'Just Expired'
            else:
                label = 'Expired'
        elif days_left <= 30:
            status = 'warning'
            label = 'Expiring Soon'
        else:
            status = 'success'
            label = 'Active'
            
        return {
            'percentage': percentage,
            'is_expired': is_expired,
            'days_left': days_left,
            'status': status,
            'label': label,
            'elapsed_days': elapsed,
            'overdue_days': max(elapsed - total_days, 0),
            'expiry_date': expiry_date
        }

    def save(self, *args, **kwargs):
        # Standardize phone
        if self.phone:
            self.phone = clean_phone_number(self.phone)

        # Track state before save
        is_new = self.pk is None
        old_instance = None
        if not is_new:
            try:
                old_instance = Patient.objects.get(pk=self.pk)
            except Patient.DoesNotExist:
                pass
        
        # Save record
        super().save(*args, **kwargs)

        # Log initial creation
        if is_new:
            PatientStatus.objects.create(
                patient=self,
                activity_type='Added',
                description="Patient registered in directory"
            )

        # Log change if plan or enrollment date changed
        if old_instance:
            tier_map = {'Gold': 3, 'Silver': 2, 'Bronze': 1, None: 0, '': 0}
            old_val = tier_map.get(old_instance.membership_plan, 0)
            new_val = tier_map.get(self.membership_plan, 0)
            
            plan_changed = old_instance.membership_plan != self.membership_plan
            date_changed = old_instance.enrollment_date != self.enrollment_date
            
            if plan_changed or (date_changed and self.membership_plan):
                if plan_changed:
                    change_type = 'Upgrade' if new_val > old_val else 'Downgrade'
                else:
                    change_type = 'Renewal'
                
                PlanHistory.objects.create(
                    patient=self,
                    old_plan=old_instance.membership_plan or 'None',
                    new_plan=self.membership_plan or 'None',
                    change_type=change_type
                )
                
                # Also log to general status
                PatientStatus.objects.create(
                    patient=self,
                    activity_type='Plan Updated' if plan_changed else 'Plan Renewed',
                    description=f"{change_type}: {old_instance.membership_plan or 'None'} → {self.membership_plan or 'None'}"
                )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class EmailSignature(models.Model):
    """Reusable HTML signatures for emails."""
    name = models.CharField(max_length=100, verbose_name="Signature Name")
    content = models.TextField(verbose_name="Signature Content (HTML)")
    is_default = models.BooleanField(default=False, verbose_name="Default Signature")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-is_default', 'name']

class MessageTemplate(models.Model):
    TEMPLATE_TYPE_CHOICES = [
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Template Name")
    type = models.CharField(max_length=10, choices=TEMPLATE_TYPE_CHOICES, default='Email', verbose_name="Type")
    subject = models.CharField(max_length=200, blank=True, null=True, verbose_name="Email Subject")
    body = models.TextField(verbose_name="Message Body", help_text="Use placeholders like {first_name}, {last_name}")
    signature = models.ForeignKey(EmailSignature, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Default Signature")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ScheduledWish(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Sent', 'Sent'),
        ('Failed', 'Failed'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='scheduled_wishes')
    template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    CHANNEL_CHOICES = [
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    ]
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='Email')
    scheduled_for = models.DateTimeField(verbose_name="Scheduled For")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Email specific options
    custom_subject = models.CharField(max_length=200, blank=True, null=True, verbose_name="Custom Subject")
    custom_body = models.TextField(blank=True, null=True, verbose_name="Custom Body")
    cc_recipients = models.CharField(max_length=500, blank=True, null=True, help_text="Comma separated emails")
    bcc_recipients = models.CharField(max_length=500, blank=True, null=True, help_text="Comma separated emails")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wish for {self.patient} on {self.scheduled_for.date()}"
    
    class Meta:
        ordering = ['scheduled_for']

class SavedRecipient(models.Model):
    """Store saved CC/BCC recipients for quick selection."""
    RECIPIENT_TYPE_CHOICES = [
        ('CC', 'CC'),
        ('BCC', 'BCC'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Recipient Name")
    email = models.EmailField(verbose_name="Email Address")
    recipient_type = models.CharField(max_length=5, choices=RECIPIENT_TYPE_CHOICES, default='CC')
    is_default = models.BooleanField(default=False, verbose_name="Select by Default")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    class Meta:
        ordering = ['-is_default', 'name']

class PatientStatus(models.Model):
    """Activity log for each patient."""
    ACTIVITY_TYPE_CHOICES = [
        ('Added', 'Patient Added'),
        ('Email Sent', 'Email Sent'),
        ('SMS Sent', 'SMS Sent'),
        ('Plan Updated', 'Plan Updated'),
        ('Details Updated', 'Details Updated'),
        ('Opt-out', 'Communication Opt-out'),
        ('Opt-in', 'Communication Opt-in'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True, help_text="Brief summary (e.g., Email Subject)")
    full_content = models.TextField(blank=True, null=True, help_text="Full detail (e.g., Email Body)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.activity_type} for {self.patient.first_name} at {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Patient Statuses"


class PlanHistory(models.Model):
    """Specific logs for plan transitions to power analytics."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='plan_history')
    old_plan = models.CharField(max_length=20)
    new_plan = models.CharField(max_length=20)
    change_type = models.CharField(max_length=20) # 'Upgrade' or 'Downgrade'
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.first_name} {self.change_type}: {self.old_plan} -> {self.new_plan}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Plan History"


class MembershipPlan(models.Model):
    """
    Define membership plans (Bronze, Silver, Gold) with pricing, benefits, and discounts.
    This allows the practice to configure their plans dynamically.
    """
    PLAN_TIER_CHOICES = [
        ('Bronze', 'Bronze'),
        ('Silver', 'Silver'),
        ('Gold', 'Gold'),
    ]
    
    name = models.CharField(max_length=50, unique=True, verbose_name="Plan Name")
    tier = models.CharField(max_length=20, choices=PLAN_TIER_CHOICES, unique=True, verbose_name="Plan Tier")
    annual_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Annual Price ($)")
    description = models.TextField(blank=True, null=True, verbose_name="Plan Description")
    
    # Included Services (free with membership)
    included_services = models.JSONField(default=list, blank=True, verbose_name="Included Services",
        help_text="List of services included at no extra charge")
    
    # Discount percentages for different service categories
    preventive_discount = models.IntegerField(default=0, verbose_name="Preventive Discount (%)")
    restorative_discount = models.IntegerField(default=0, verbose_name="Restorative Discount (%)")
    cosmetic_discount = models.IntegerField(default=0, verbose_name="Cosmetic Discount (%)")
    implant_discount = models.IntegerField(default=0, verbose_name="Implant Discount (%)")
    
    # Display settings
    color = models.CharField(max_length=7, default="#6366f1", verbose_name="Display Color (Hex)")
    icon = models.CharField(max_length=50, default="bi-star", verbose_name="Bootstrap Icon Class")
    is_featured = models.BooleanField(default=False, verbose_name="Featured Plan")
    display_order = models.IntegerField(default=0, verbose_name="Display Order")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (${self.annual_price}/year)"
    
    class Meta:
        ordering = ['display_order', 'tier']
        verbose_name = "Membership Plan"
        verbose_name_plural = "Membership Plans"


class Campaign(models.Model):
    """
    Automated campaign system for birthday wishes, renewal reminders, and promotions.
    """
    TRIGGER_TYPE_CHOICES = [
        ('birthday', 'Birthday (On Day)'),
        ('birthday_before', 'Birthday (Days Before)'),
        ('expiring_30', 'Plan Expiring in 30 Days'),
        ('expiring_14', 'Plan Expiring in 14 Days'),
        ('expiring_7', 'Plan Expiring in 7 Days'),
        ('expired', 'Plan Just Expired'),
        ('grace_ending', 'Grace Period Ending (25 Days)'),
        ('anniversary', 'Membership Anniversary'),
        ('upgrade_promo', 'Upgrade Promotion'),
        ('welcome', 'Welcome New Member'),
        ('manual', 'Manual Trigger Only'),
    ]
    
    CHANNEL_CHOICES = [
        ('Email', 'Email Only'),
        ('SMS', 'SMS Only'),
        ('Both', 'Email & SMS'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Campaign Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPE_CHOICES, verbose_name="Trigger Type")
    
    # Timing
    days_before = models.IntegerField(default=0, verbose_name="Days Before Event",
        help_text="For birthday_before trigger, how many days before")
    send_time = models.TimeField(default="09:00", verbose_name="Send Time")
    
    # Target audience
    target_plans = models.JSONField(default=list, blank=True, verbose_name="Target Plans",
        help_text="Leave empty for all plans, or specify ['Bronze', 'Silver', 'Gold']")
    target_patient_type = models.CharField(max_length=20, blank=True, null=True,
        choices=[('Regular', 'Regular'), ('Proceed', 'Proceed')],
        verbose_name="Target Patient Type")
    
    # Communication
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='Email', verbose_name="Channel")
    email_template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='email_campaigns', verbose_name="Email Template")
    sms_template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sms_campaigns', verbose_name="SMS Template")
    
    # Status
    is_active = models.BooleanField(default=False, verbose_name="Active")
    
    # Stats
    total_sent = models.IntegerField(default=0, verbose_name="Total Sent")
    last_run = models.DateTimeField(blank=True, null=True, verbose_name="Last Run")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_trigger_type_display()})"
    
    class Meta:
        ordering = ['trigger_type', 'name']
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"


class CampaignExecution(models.Model):
    """Log each campaign run for tracking and analytics."""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='executions')
    executed_at = models.DateTimeField(auto_now_add=True)
    patients_targeted = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    sms_sent = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.campaign.name} - {self.executed_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-executed_at']


class CommunicationLog(models.Model):
    """Detailed log of all communications sent."""
    CHANNEL_CHOICES = [
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    ]
    STATUS_CHOICES = [
        ('Sent', 'Sent'),
        ('Failed', 'Failed'),
        ('Pending', 'Pending'),
    ]
    DIRECTION_CHOICES = [
        ('Outbound', 'Outbound'),
        ('Inbound', 'Inbound'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='communications', null=True, blank=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='Outbound')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    subject = models.CharField(max_length=200, blank=True, null=True)
    body = models.TextField()
    recipient = models.CharField(max_length=200)  # Email or phone number
    external_message_id = models.CharField(max_length=100, blank=True, null=True)
    gateway_number = models.CharField(max_length=30, blank=True, null=True, help_text="Twilio number used for this SMS")
    
    sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.channel} to {self.patient} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Communication Log"
        verbose_name_plural = "Communication Logs"


class PracticeSettings(models.Model):
    """Global settings for the practice."""
    practice_name = models.CharField(max_length=200, default="Implants Guru", verbose_name="Practice Name")
    practice_phone = models.CharField(max_length=20, default="760-340-5107", verbose_name="Practice Phone")
    practice_email = models.EmailField(default="info@implantsguru.dentist", verbose_name="Practice Email")
    practice_address = models.TextField(blank=True, null=True, verbose_name="Practice Address")
    practice_website = models.URLField(default="https://www.implantsguru.dentist", verbose_name="Website")
    
    # Plan settings
    reinstatement_fee = models.DecimalField(max_digits=6, decimal_places=2, default=50.00,
        verbose_name="Reinstatement Fee ($)")
    grace_period_days = models.IntegerField(default=30, verbose_name="Grace Period (Days)")
    plan_duration_days = models.IntegerField(default=365, verbose_name="Plan Duration (Days)")
    
    # Enrollment link
    enrollment_base_url = models.URLField(
        default="https://portal.sivahub.com/SivaForms/SecuredForms/ClientHTMLForms/1864/Dental-Savings-Membership-Plan",
        verbose_name="Enrollment Form URL")
    
    # Email settings
    from_email = models.EmailField(default="noreply@implantsguru.dentist", verbose_name="From Email")
    reply_to_email = models.EmailField(blank=True, null=True, verbose_name="Reply-To Email")
    
    # SMS settings
    sms_enabled = models.BooleanField(default=True, verbose_name="SMS Enabled")
    sms_sender_name = models.CharField(max_length=20, default="ImplantsGuru", verbose_name="SMS Sender Name")
    
    # Auto-campaign settings
    auto_birthday_wishes = models.BooleanField(default=True, verbose_name="Auto Birthday Wishes")
    auto_renewal_reminders = models.BooleanField(default=True, verbose_name="Auto Renewal Reminders")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.practice_name
    
    class Meta:
        verbose_name = "Practice Settings"
        verbose_name_plural = "Practice Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings record exists
        if not self.pk and PracticeSettings.objects.exists():
            raise ValueError("Only one PracticeSettings instance is allowed")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class ServicePricing(models.Model):
    """Define services and their pricing for each plan tier."""
    CATEGORY_CHOICES = [
        ('Preventive', 'Preventive'),
        ('Restorative', 'Restorative'),
        ('Cosmetic', 'Cosmetic'),
        ('Implant', 'Implant'),
        ('Other', 'Other'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Service Name")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="Category")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    
    # Regular pricing (no membership)
    regular_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Regular Price ($)")
    
    # Plan-specific pricing (override discount if needed)
    bronze_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True,
        verbose_name="Bronze Price ($)")
    silver_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True,
        verbose_name="Silver Price ($)")
    gold_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True,
        verbose_name="Gold Price ($)")
    
    # If true, this service is included free with the plan
    included_in_bronze = models.BooleanField(default=False, verbose_name="Included in Bronze")
    included_in_silver = models.BooleanField(default=False, verbose_name="Included in Silver")
    included_in_gold = models.BooleanField(default=False, verbose_name="Included in Gold")
    
    display_order = models.IntegerField(default=0, verbose_name="Display Order")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (${self.regular_price})"
    
    class Meta:
        ordering = ['category', 'display_order', 'name']
        verbose_name = "Service Pricing"
        verbose_name_plural = "Service Pricing"
