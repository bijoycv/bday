import os

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Patient, PatientStatus, ScheduledWish


class DailyReportApiTests(TestCase):
    def setUp(self):
        self.original_token = os.environ.get('REPORT_API_TOKEN')
        os.environ['REPORT_API_TOKEN'] = 'test-report-token'
        self.url = reverse('daily_report_api')
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            dob='1990-01-01',
            phone='5551234567',
            email='john@example.com',
        )

    def tearDown(self):
        if self.original_token is None:
            os.environ.pop('REPORT_API_TOKEN', None)
        else:
            os.environ['REPORT_API_TOKEN'] = self.original_token

    def test_daily_report_api_requires_token(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'error')

    def test_daily_report_api_returns_report_payload(self):
        activity = PatientStatus.objects.create(
            patient=self.patient,
            activity_type='Email Sent',
            description='Birthday email sent',
            full_content='Happy Birthday',
        )
        failure = ScheduledWish.objects.create(
            patient=self.patient,
            channel='SMS',
            scheduled_for=timezone.now(),
            status='Failed',
            error_message='Twilio delivery failed',
        )

        now = timezone.now()
        PatientStatus.objects.filter(pk=activity.pk).update(created_at=now)
        ScheduledWish.objects.filter(pk=failure.pk).update(updated_at=now)

        response = self.client.get(
            self.url,
            HTTP_X_API_KEY='test-report-token',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(payload['report']['summary']['total_sent'], 1)
        self.assertEqual(payload['report']['summary']['emails_count'], 1)
        self.assertEqual(payload['report']['summary']['sms_count'], 0)
        self.assertEqual(payload['report']['summary']['total_failed'], 1)
        self.assertEqual(payload['report']['summary']['birthdays_total'], 0)
        self.assertEqual(payload['report']['summary']['birthdays_wished'], 0)
        self.assertEqual(len(payload['report']['activities']), 1)
        self.assertEqual(len(payload['report']['failures']), 1)
        self.assertEqual(payload['report']['activities'][0]['patient']['email'], 'john@example.com')

    def test_daily_report_api_includes_today_birthday_wish_details(self):
        today = timezone.localdate()
        birthday_patient = Patient.objects.create(
            first_name='Birthday',
            last_name='Patient',
            dob=today.replace(year=1995),
            phone='5551112222',
            email='birthday@example.com',
        )
        activity = PatientStatus.objects.create(
            patient=birthday_patient,
            activity_type='SMS Sent',
            description='Birthday wish sent',
        )
        now = timezone.now()
        PatientStatus.objects.filter(pk=activity.pk).update(created_at=now)

        response = self.client.get(
            self.url,
            HTTP_X_API_KEY='test-report-token',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['report']['summary']['birthdays_total'], 1)
        self.assertEqual(payload['report']['summary']['birthdays_wished'], 1)
        self.assertEqual(payload['report']['summary']['birthdays_unwished'], 0)
        self.assertEqual(payload['report']['birthdays']['total'], 1)
        self.assertEqual(payload['report']['birthdays']['wished'], 1)
        self.assertEqual(len(payload['report']['birthdays']['details']), 1)
        self.assertEqual(payload['report']['birthdays']['details'][0]['email'], 'birthday@example.com')
        self.assertTrue(payload['report']['birthdays']['details'][0]['is_wished_today'])

    def test_daily_report_api_rejects_invalid_date(self):
        response = self.client.get(
            f'{self.url}?date=2026-99-99',
            HTTP_AUTHORIZATION='Bearer test-report-token',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_daily_report_api_filters_by_date(self):
        activity = PatientStatus.objects.create(
            patient=self.patient,
            activity_type='SMS Sent',
            description='Birthday SMS sent',
        )
        yesterday = timezone.now() - timezone.timedelta(days=1)
        PatientStatus.objects.filter(pk=activity.pk).update(created_at=yesterday)

        today_response = self.client.get(
            self.url,
            HTTP_X_API_KEY='test-report-token',
        )
        yesterday_response = self.client.get(
            f'{self.url}?date={yesterday.date().isoformat()}',
            HTTP_X_API_KEY='test-report-token',
        )

        self.assertEqual(today_response.json()['report']['summary']['total_sent'], 0)
        self.assertEqual(yesterday_response.json()['report']['summary']['total_sent'], 1)


class DailyReportApiDocsTests(TestCase):
    def test_docs_page_renders(self):
        response = self.client.get(reverse('daily_report_api_docs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/api/reports/daily/')
