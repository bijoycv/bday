from django.urls import path
from . import views, reports

urlpatterns = [
    path('', views.index, name='index'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/add/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_update, name='patient_update'),
    path('patients/<int:pk>/delete/', views.patient_delete, name='patient_delete'),
    path('patients/bulk-delete/', views.patient_bulk_delete, name='patient_bulk_delete'),
    path('patients/<int:pk>/toggle-verification/', views.toggle_patient_verification, name='toggle_patient_verification'),
    path('patients/<int:pk>/toggle-communication/', views.toggle_communication_status, name='toggle_communication_status'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_update, name='template_update'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    
    # Scheduled Wishes
    path('scheduled/', views.scheduled_list, name='scheduled_list'),
    path('scheduled/add/', views.schedule_wish, name='schedule_wish'),
    path('scheduled/add/<int:patient_id>/', views.schedule_wish, name='schedule_wish_for_patient'),
    
    # Quick Actions
    path('send-message/', views.quick_send_message, name='quick_send_message'),
    
    # Scheduled
    path('scheduled/<int:pk>/edit/', views.scheduled_update, name='scheduled_update'),
    path('scheduled/<int:pk>/delete/', views.scheduled_delete, name='scheduled_delete'),
    path('scheduled/bulk-delete/', views.scheduled_bulk_delete, name='scheduled_bulk_delete'),
    
    # Saved Recipients (CC/BCC)
    path('recipients/', views.recipient_list, name='recipient_list'),
    path('recipients/add/', views.recipient_create, name='recipient_create'),
    path('recipients/<int:pk>/edit/', views.recipient_update, name='recipient_update'),
    path('recipients/<int:pk>/delete/', views.recipient_delete, name='recipient_delete'),

    # Email Signatures
    path('signatures/', views.signature_list, name='signature_list'),
    path('signatures/create/', views.signature_create, name='signature_create'),
    path('signatures/<int:pk>/edit/', views.signature_update, name='signature_update'),
    path('signatures/<int:pk>/delete/', views.signature_delete, name='signature_delete'),

    # Reports
    path('reports/', reports.report_dashboard, name='report_dashboard'),
    path('reports/generate/', reports.generate_report, name='generate_report'),
    path('reports/mark-outreach/', reports.mark_outreach_status, name='mark_outreach_status'),
    path('reports/email/', reports.email_report_trigger, name='email_report_trigger'),
    path('reports/daily-summary/', reports.email_daily_summary_trigger, name='email_daily_summary_trigger'),
    path('scheduled/update-ajax/<int:pk>/', views.scheduled_update_ajax, name='scheduled_update_ajax'),

    # SMO Sync
    path('sync/practices/', views.sync_practices, name='sync_practices'),
    path('sync/practices/<int:practice_id>/delete/', views.delete_practice, name='delete_practice'),
    path('sync/patients/<int:practice_id>/', views.sync_practice_patients, name='sync_practice_patients'),
    path('sync/patients/<int:practice_id>/preview/', views.preview_sync_patients, name='preview_sync_patients'),
    path('sync/patients/bulk-sync/', views.confirm_bulk_sync, name='confirm_bulk_sync'),

    # --- Proceed Plan Management System ---
    # Membership Plans
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<int:pk>/edit/', views.plan_update, name='plan_update'),
    path('plans/<int:pk>/delete/', views.plan_delete, name='plan_delete'),

    # Service Pricing
    path('services/', views.service_list, name='service_list'),
    path('services/create/', views.service_create, name='service_create'),
    path('services/<int:pk>/edit/', views.service_update, name='service_update'),
    path('services/<int:pk>/delete/', views.service_delete, name='service_delete'),

    # Campaigns
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/edit/', views.campaign_update, name='campaign_update'),
    path('campaigns/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    path('campaigns/<int:pk>/run/', views.campaign_run, name='campaign_run'),

    # Practice Settings
    path('settings/', views.practice_settings, name='practice_settings'),

    # Analytics Dashboard
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),

    # Communication Logs
    path('communications/', views.communication_log_list, name='communication_log_list'),
    path('messages/', views.messages_hub, name='messages_hub'),
    path('messages/send/', views.send_direct_sms, name='send_direct_sms'),
    path('messages/twilio/webhook/', views.twilio_sms_webhook, name='twilio_sms_webhook'),
]
