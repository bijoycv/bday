from django import forms
from .models import Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = '__all__'
        exclude = ['created_at', 'updated_at', 'unsubscribed_at']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Date of Birth'}),
            'enrollment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address...'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip Code'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Extra notes...'}),
            'membership_plan': forms.Select(attrs={'class': 'form-select'}),
            'patient_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 1.5em; height: 1.5em;'}),
            'accepts_marketing': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 1.5em; height: 1.5em;'}),
            'unsubscribe_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason for opting out...'}),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class UploadFileForm(forms.Form):
    file = forms.FileField(required=True, widget=MultipleFileInput(attrs={'class': 'form-control', 'accept': '.txt', 'id': 'patient-file-input'}))

from .models import MessageTemplate, ScheduledWish, EmailSignature

class EmailSignatureForm(forms.ModelForm):
    class Meta:
        model = EmailSignature
        fields = ['name', 'content', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Office Main Signature'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'HTML signature content...'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ['name', 'type', 'subject', 'body', 'signature']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Standard Birthday Wish'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Happy Birthday!'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Hi {first_name}, ...'}),
            'signature': forms.Select(attrs={'class': 'form-select'}),
        }

class ScheduledWishForm(forms.ModelForm):
    class Meta:
        model = ScheduledWish
        fields = ['patient', 'template', 'scheduled_for', 'cc_recipients', 'bcc_recipients']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_for': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'cc_recipients': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'email1@example.com, email2@example.com'}),
            'bcc_recipients': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'email3@example.com'}),
        }

from .models import SavedRecipient

class SavedRecipientForm(forms.ModelForm):
    class Meta:
        model = SavedRecipient
        fields = ['name', 'email', 'recipient_type', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Office Admin'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'recipient_type': forms.Select(attrs={'class': 'form-select'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# --- New Forms for Plan Management System ---
from .models import MembershipPlan, Campaign, PracticeSettings, ServicePricing

class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = [
            'name', 'tier', 'annual_price', 'description',
            'preventive_discount', 'restorative_discount', 'cosmetic_discount', 'implant_discount',
            'color', 'icon', 'is_featured', 'display_order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Gold Membership'}),
            'tier': forms.Select(attrs={'class': 'form-select'}),
            'annual_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '499.00', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Plan description...'}),
            'preventive_discount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'restorative_discount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'cosmetic_discount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'implant_discount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-star-fill'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'name', 'description', 'trigger_type', 'days_before', 'send_time',
            'target_patient_type', 'channel', 'email_template', 'sms_template', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Birthday Wishes'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Campaign description...'}),
            'trigger_type': forms.Select(attrs={'class': 'form-select'}),
            'days_before': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'send_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'target_patient_type': forms.Select(attrs={'class': 'form-select'}),
            'channel': forms.Select(attrs={'class': 'form-select'}),
            'email_template': forms.Select(attrs={'class': 'form-select'}),
            'sms_template': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PracticeSettingsForm(forms.ModelForm):
    class Meta:
        model = PracticeSettings
        fields = [
            'practice_name', 'practice_phone', 'practice_email', 'practice_address', 'practice_website',
            'reinstatement_fee', 'grace_period_days', 'plan_duration_days', 'enrollment_base_url',
            'from_email', 'reply_to_email', 'sms_enabled', 'sms_sender_name',
            'auto_birthday_wishes', 'auto_renewal_reminders'
        ]
        widgets = {
            'practice_name': forms.TextInput(attrs={'class': 'form-control'}),
            'practice_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'practice_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'practice_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'practice_website': forms.URLInput(attrs={'class': 'form-control'}),
            'reinstatement_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'plan_duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'enrollment_base_url': forms.URLInput(attrs={'class': 'form-control'}),
            'from_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'reply_to_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'sms_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_sender_name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 20}),
            'auto_birthday_wishes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_renewal_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ServicePricingForm(forms.ModelForm):
    class Meta:
        model = ServicePricing
        fields = [
            'name', 'category', 'description', 'regular_price',
            'bronze_price', 'silver_price', 'gold_price',
            'included_in_bronze', 'included_in_silver', 'included_in_gold',
            'display_order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Comprehensive Exam'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'regular_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bronze_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'silver_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'gold_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'included_in_bronze': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'included_in_silver': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'included_in_gold': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
