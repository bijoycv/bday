from datetime import date, timedelta

from django.db.models import Exists, OuterRef

from .models import Patient, PatientStatus, ScheduledWish


def todays_birthdays_popup(request):
    """Global context for a bottom-right popup with today's birthday actions."""
    try:
        today = date.today()
        
        def get_birthday_data(target_date):
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

            patients = list(
                Patient.objects.filter(dob__month=target_date.month, dob__day=target_date.day)
                .annotate(
                    has_pending_wish=Exists(pending_wish_qs),
                    has_sent_wish=Exists(sent_wish_qs),
                    has_sent_activity=Exists(sent_activity_qs),
                )
                .order_by("first_name", "last_name")[:8]
            )
            
            for patient in patients:
                patient.age_turning = target_date.year - patient.dob.year
            
            count = Patient.objects.filter(dob__month=target_date.month, dob__day=target_date.day).count()
            return patients, count

        # Try today first
        todays_birthdays, total_today = get_birthday_data(today)
        
        # Check if today is "done"
        is_today_done = total_today > 0 and all(
            p.has_pending_wish or p.has_sent_wish or p.has_sent_activity 
            for p in todays_birthdays
        )
        
        # If today has no birthdays OR all today's are done, check tomorrow
        if total_today == 0 or is_today_done:
            tomorrow = today + timedelta(days=1)
            tomorrows_birthdays, total_tomorrow = get_birthday_data(tomorrow)
            
            if total_tomorrow > 0:
                return {
                    "todays_birthdays_popup": tomorrows_birthdays,
                    "todays_birthdays_popup_count": total_tomorrow,
                    "todays_birthdays_popup_date": today.strftime("%Y-%m-%d"),
                    "is_tomorrow": True,
                }

        # Default to today (even if empty, base.html handles count > 0)
        return {
            "todays_birthdays_popup": todays_birthdays,
            "todays_birthdays_popup_count": total_today,
            "todays_birthdays_popup_date": today.strftime("%Y-%m-%d"),
            "is_tomorrow": False,
        }
    except Exception:
        # Keep all pages usable even if DB is not ready (e.g., migrations/startup).
        return {
            "todays_birthdays_popup": [],
            "todays_birthdays_popup_count": 0,
            "todays_birthdays_popup_date": date.today().strftime("%Y-%m-%d"),
            "is_tomorrow": False,
        }
