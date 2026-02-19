from datetime import date

from django.db.models import Exists, OuterRef

from .models import Patient, PatientStatus, ScheduledWish


def todays_birthdays_popup(request):
    """Global context for a bottom-right popup with today's birthday actions."""
    try:
        today = date.today()

        pending_wish_qs = ScheduledWish.objects.filter(
            patient_id=OuterRef("pk"),
            status="Pending",
        )
        sent_wish_qs = ScheduledWish.objects.filter(
            patient_id=OuterRef("pk"),
            status="Sent",
        )
        sent_activity_qs = PatientStatus.objects.filter(
            patient_id=OuterRef("pk"),
            activity_type__in=["Email Sent", "SMS Sent"],
        )

        todays_birthdays = list(
            Patient.objects.filter(dob__month=today.month, dob__day=today.day)
            .annotate(
                has_pending_wish=Exists(pending_wish_qs),
                has_sent_wish=Exists(sent_wish_qs),
                has_sent_activity=Exists(sent_activity_qs),
            )
            .order_by("first_name", "last_name")[:8]
        )

        for patient in todays_birthdays:
            patient.age_turning = today.year - patient.dob.year

        total_today = Patient.objects.filter(dob__month=today.month, dob__day=today.day).count()

        return {
            "todays_birthdays_popup": todays_birthdays,
            "todays_birthdays_popup_count": total_today,
            "todays_birthdays_popup_date": today.strftime("%Y-%m-%d"),
        }
    except Exception:
        # Keep all pages usable even if DB is not ready (e.g., migrations/startup).
        return {
            "todays_birthdays_popup": [],
            "todays_birthdays_popup_count": 0,
            "todays_birthdays_popup_date": date.today().strftime("%Y-%m-%d"),
        }
